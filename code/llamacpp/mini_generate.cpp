// mini_generate.cpp: the smallest useful program on top of libllama.
//
// It loads a GGUF model, shows the 5 most likely first tokens (raw logits),
// then generates text with a sampler chain and prints its speed and KV cache use.
// It uses the new batch API (llama_batch_ext + llama_process), the same one
// examples/simple/simple.cpp uses at llama.cpp commit 0fb8f15.
//
// Build (after building llama.cpp in $LLAMA with cmake):
//   g++ -std=c++17 -O2 mini_generate.cpp -I$LLAMA/include -I$LLAMA/ggml/include \
//       -L$LLAMA/build/bin -lllama -lggml -lggml-base -Wl,-rpath,$LLAMA/build/bin -o mini_generate
// Run:
//   ./mini_generate tiny-llama-Q8_0.gguf "The KV cache" 40

#include "llama.h"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

static std::string piece(const llama_vocab * vocab, llama_token t) {
    char buf[256];
    int n = llama_token_to_piece(vocab, t, buf, sizeof(buf), 0, true);
    return n > 0 ? std::string(buf, n) : std::string();
}

int main(int argc, char ** argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s model.gguf \"prompt\" [n_predict]\n", argv[0]);
        return 1;
    }
    const char * path   = argv[1];
    std::string  prompt = argv[2];
    const int    n_predict = argc > 3 ? atoi(argv[3]) : 32;

    // 1. Load every backend this build has (CPU, and CUDA/Metal/Vulkan if built), quietly.
    llama_log_set([](ggml_log_level lvl, const char * text, void *) {
        if (lvl >= GGML_LOG_LEVEL_ERROR) fputs(text, stderr);
    }, nullptr);
    llama_backend_init();
    ggml_backend_load_all();

    // 2. The model: weights + vocab, memory-mapped from the GGUF file.
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = 99;  // ignored on a CPU-only build
    mp.progress_callback = [](float, void *) { return true; };  // no loading dots
    llama_model * model = llama_model_load_from_file(path, mp);
    if (!model) { fprintf(stderr, "could not load %s\n", path); return 1; }
    const llama_vocab * vocab = llama_model_get_vocab(model);

    char desc[128];
    llama_model_desc(model, desc, sizeof(desc));
    printf("model: %s, %.1fM params, vocab %d\n", desc, llama_model_n_params(model) / 1e6, llama_vocab_n_tokens(vocab));

    // 3. Tokenize. The first call with no buffer returns minus the number of tokens.
    const int n_prompt = -llama_tokenize(vocab, prompt.c_str(), prompt.size(), nullptr, 0, true, true);
    std::vector<llama_token> tokens(n_prompt);
    llama_tokenize(vocab, prompt.c_str(), prompt.size(), tokens.data(), n_prompt, true, true);
    printf("prompt tokens:");
    for (auto t : tokens) printf(" %d='%s'", t, piece(vocab, t).c_str());
    printf("\n");

    // 4. The context: KV cache + compute buffers. One per conversation stream.
    llama_context_params cp = llama_context_default_params();
    cp.n_ctx   = n_prompt + n_predict;
    cp.n_batch = n_prompt;
    cp.no_perf = false;
    llama_context * ctx = llama_init_from_model(model, cp);

    // 5. The sampler chain, the same shape as the example in llama.h.
    llama_sampler * smpl = llama_sampler_chain_init(llama_sampler_chain_default_params());
    llama_sampler_chain_add(smpl, llama_sampler_init_top_k(40));
    llama_sampler_chain_add(smpl, llama_sampler_init_top_p(0.95f, 1));
    llama_sampler_chain_add(smpl, llama_sampler_init_temp(0.7f));
    llama_sampler_chain_add(smpl, llama_sampler_init_dist(42));

    // 6. Prefill: the whole prompt in one batch, logits only for the last token.
    llama_batch_ext * batch = llama_batch_ext_init(ctx);
    auto fill = [&](const llama_token * toks, int n, llama_pos pos0) {
        llama_batch_ext_clear(batch);
        for (int i = 0; i < n; i++) {
            int idx = llama_batch_ext_add_token(batch, 0, toks[i]);
            llama_pos pos = pos0 + i;
            llama_batch_ext_set_pos(batch, idx, &pos);
        }
        llama_batch_ext_set_output_logits(batch, n - 1, true);
    };
    fill(tokens.data(), n_prompt, 0);
    if (llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, batch) != 0) { fprintf(stderr, "decode failed\n"); return 1; }

    // 7. Peek at the raw logits for the next token before any sampler touches them.
    const float * logits = llama_get_logits_ith(ctx, -1);
    std::vector<llama_token> ids(llama_vocab_n_tokens(vocab));
    for (size_t i = 0; i < ids.size(); i++) ids[i] = (llama_token) i;
    std::partial_sort(ids.begin(), ids.begin() + 5, ids.end(), [&](int a, int b) { return logits[a] > logits[b]; });
    printf("top 5 next tokens:");
    for (int i = 0; i < 5; i++) printf(" '%s'(%.2f)", piece(vocab, ids[i]).c_str(), logits[ids[i]]);
    printf("\n\n%s", prompt.c_str());

    // 8. Decode loop: sample one token, feed it back, repeat.
    auto t0 = std::chrono::steady_clock::now();
    llama_pos n_pos = n_prompt;
    int n_out = 0;
    for (; n_out < n_predict; n_out++) {
        llama_token next = llama_sampler_sample(smpl, ctx, -1);
        if (llama_vocab_is_eog(vocab, next)) break;
        printf("%s", piece(vocab, next).c_str());
        fflush(stdout);
        fill(&next, 1, n_pos++);
        if (llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, batch) != 0) break;
    }
    double s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    printf("\n\n%d tokens in %.3fs = %.0f tok/s\n", n_out, s, n_out / s);

    // 9. How much of the KV cache sequence 0 now holds.
    // n_ctx is the value we asked for, rounded up to a multiple of 256.
    printf("KV cache: sequence 0 holds positions 0..%d of n_ctx %u\n",
           llama_memory_seq_pos_max(llama_get_memory(ctx), 0), llama_n_ctx(ctx));

    llama_batch_ext_free(batch);
    llama_sampler_free(smpl);
    llama_free(ctx);
    llama_model_free(model);
    return 0;
}
