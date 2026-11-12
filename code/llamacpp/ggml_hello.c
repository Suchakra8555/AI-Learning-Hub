// ggml_hello.c: ggml on its own, no llama.cpp model code.
//
// Builds one tiny "layer": y = silu(W x) + b, once with W in F32 and once with W
// quantized to Q4_0. Shows that defining the graph computes nothing, prints the
// graph's nodes, then computes it on the CPU and compares the two answers.
//
// Build (after building llama.cpp in $LLAMA):
//   gcc -O2 ggml_hello.c -I$LLAMA/ggml/include -L$LLAMA/build/bin \
//       -lggml -lggml-base -lggml-cpu -lm -Wl,-rpath,$LLAMA/build/bin -o ggml_hello
// Run:
//   ./ggml_hello

#include "ggml.h"
#include "ggml-cpu.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N_IN  64   // ne0 of W: must be a multiple of 32 for Q4_0 blocks
#define N_OUT 4    // ne1 of W: rows

static struct ggml_tensor * layer(struct ggml_context * ctx, struct ggml_tensor * W,
                                  struct ggml_tensor * x, struct ggml_tensor * b) {
    // ggml_mul_mat(a, b) gives a tensor of shape [a->ne[1], b->ne[1]]: one dot product
    // per row of a. So W is stored as N_OUT rows of N_IN numbers.
    struct ggml_tensor * Wx = ggml_mul_mat(ctx, W, x);
    return ggml_add(ctx, ggml_silu(ctx, Wx), b);
}

int main(void) {
    // An arena of 16 MiB. Every tensor below, data included, lives inside it.
    struct ggml_init_params params = { .mem_size = 16 * 1024 * 1024, .mem_buffer = NULL, .no_alloc = false };
    struct ggml_context * ctx = ggml_init(params);

    struct ggml_tensor * W   = ggml_new_tensor_2d(ctx, GGML_TYPE_F32,  N_IN, N_OUT);
    struct ggml_tensor * Wq  = ggml_new_tensor_2d(ctx, GGML_TYPE_Q4_0, N_IN, N_OUT);
    struct ggml_tensor * x   = ggml_new_tensor_1d(ctx, GGML_TYPE_F32,  N_IN);
    struct ggml_tensor * b   = ggml_new_tensor_1d(ctx, GGML_TYPE_F32,  N_OUT);
    ggml_set_name(W, "W"); ggml_set_name(Wq, "W_q4_0"); ggml_set_name(x, "x"); ggml_set_name(b, "b");

    // Fill inputs with fixed pseudo-random numbers.
    srand(1);
    float * w = (float *) W->data;
    for (int i = 0; i < N_IN * N_OUT; i++) w[i] = ((float) rand() / RAND_MAX - 0.5f) * 0.2f;
    for (int i = 0; i < N_IN; i++)        ((float *) x->data)[i] = (float) rand() / RAND_MAX;
    for (int i = 0; i < N_OUT; i++)       ((float *) b->data)[i] = 0.1f * i;

    // Quantize W into Wq: 4 rows x 2 blocks x 18 bytes = 144 bytes instead of 1024.
    ggml_quantize_chunk(GGML_TYPE_Q4_0, w, Wq->data, 0, N_OUT, N_IN, NULL);
    printf("W:  %s, %zu bytes\nWq: %s, %zu bytes\n\n",
           ggml_type_name(W->type), ggml_nbytes(W), ggml_type_name(Wq->type), ggml_nbytes(Wq));

    // Define. Nothing is computed yet: y and yq only record their op and their sources.
    struct ggml_tensor * y  = layer(ctx, W,  x, b);
    struct ggml_tensor * yq = layer(ctx, Wq, x, b);
    printf("after defining: y->op = %s, y->src[0]->op = %s\n", ggml_op_name(y->op), ggml_op_name(y->src[0]->op));

    // Build the graph: walk back from the outputs and list nodes in order.
    struct ggml_cgraph * gf = ggml_new_graph(ctx);
    ggml_build_forward_expand(gf, y);
    ggml_build_forward_expand(gf, yq);
    printf("graph has %d nodes:\n", ggml_graph_n_nodes(gf));
    for (int i = 0; i < ggml_graph_n_nodes(gf); i++) {
        struct ggml_tensor * t = ggml_graph_node(gf, i);
        printf("  %d: %-8s shape [%lld, %lld]  inputs: %s%s%s\n", i, ggml_op_desc(t),
               (long long) t->ne[0], (long long) t->ne[1],
               t->src[0] ? t->src[0]->name : "", t->src[1] ? ", " : "", t->src[1] ? t->src[1]->name : "");
    }

    // Compute, on the CPU, with 2 threads.
    ggml_graph_compute_with_ctx(ctx, gf, 2);

    printf("\n%-6s %10s %10s %10s\n", "row", "F32", "Q4_0", "diff");
    for (int i = 0; i < N_OUT; i++) {
        float a = ggml_get_f32_1d(y, i), q = ggml_get_f32_1d(yq, i);
        printf("%-6d %10.5f %10.5f %10.5f\n", i, a, q, fabsf(a - q));
    }

    ggml_free(ctx);
    return 0;
}
