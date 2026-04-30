// colorize.cpp — compiled with -fno-rtti to avoid typeinfo link error
// with libncnn.a which hides ncnn::Layer typeinfo symbols
#include <cstdio>
#include <cstring>
#include <string>
#include <net.h>
#include <layer.h>

class Sig17Slice : public ncnn::Layer {
public:
    Sig17Slice() { one_blob_only = true; }
    int forward(const ncnn::Mat& bottom_blob, ncnn::Mat& top_blob,
                const ncnn::Option& opt) const override {
        int w = bottom_blob.w, h = bottom_blob.h, c = bottom_blob.c;
        int ow = w/2, oh = h/2;
        top_blob.create(ow, oh, c, 4u, 1, opt.blob_allocator);
        if (top_blob.empty()) return -100;
        for (int p = 0; p < c; p++) {
            const float* ptr = bottom_blob.channel(p%c).row((p/c)%2) + ((p/c)/2);
            float* outptr = top_blob.channel(p);
            for (int i = 0; i < oh; i++) {
                for (int j = 0; j < ow; j++) { *outptr++ = *ptr; ptr += 2; }
                ptr += w;
            }
        }
        return 0;
    }
};
DEFINE_LAYER_CREATOR(Sig17Slice)

// C linkage — no name mangling, callable from main.cpp compiled with -frtti
extern "C" int colorize_image(
        const float* L_256,        // input: L channel 256x256 float
        float* ab_out,             // output: ab channels + [w,h] at end
        const char* model_dir)
{
    ncnn::Net net;
    net.opt.use_vulkan_compute = false;
    net.opt.num_threads = 2;
    net.register_custom_layer("Sig17Slice", Sig17Slice_layer_creator);

    std::string mp(model_dir);
    if (net.load_param((mp + "/siggraph17_color_sim.param").c_str())) return -1;
    if (net.load_model((mp + "/siggraph17_color_sim.bin").c_str()))   return -1;

    ncnn::Mat in(256, 256, 1, (void*)L_256);
    in = in.clone();

    ncnn::Extractor ex = net.create_extractor();
    ex.input("input", in);
    ncnn::Mat out;
    ex.extract("out_ab", out);
    if (out.empty()) return -2;

    int n = out.w * out.h;
    memcpy(ab_out,     out.data,                  n * sizeof(float));
    memcpy(ab_out + n, (float*)out.data + n,      n * sizeof(float));
    ab_out[n*2]   = (float)out.w;
    ab_out[n*2+1] = (float)out.h;
    return 0;
}
