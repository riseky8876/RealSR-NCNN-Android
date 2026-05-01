#!/usr/bin/env python3
"""Generates colorize-ncnn C++ sources into colorize-src/"""
import sys, os

ncnn_dir   = os.path.abspath(sys.argv[1])
opencv_dir = os.path.abspath(sys.argv[2])

os.makedirs("colorize-src", exist_ok=True)

print(f"ncnn_DIR  (abs): {ncnn_dir}")
print(f"opencv_DIR (abs): {opencv_dir}")

ncnn_cfg   = os.path.join(ncnn_dir,   "ncnnConfig.cmake")
opencv_cfg = os.path.join(opencv_dir, "OpenCVConfig.cmake")
if not os.path.exists(ncnn_cfg):
    print(f"ERROR: {ncnn_cfg} not found!", file=sys.stderr); sys.exit(1)
if not os.path.exists(opencv_cfg):
    print(f"ERROR: {opencv_cfg} not found!", file=sys.stderr); sys.exit(1)

cmake = (
    "cmake_minimum_required(VERSION 3.22)\n"
    "project(colorize-ncnn)\n"
    "set(CMAKE_CXX_STANDARD 17)\n"
    f'set(ncnn_DIR "{ncnn_dir}")\n'
    f'set(OpenCV_DIR "{opencv_dir}")\n'
    "find_package(ncnn REQUIRED)\n"
    "set_target_properties(ncnn PROPERTIES INTERFACE_COMPILE_OPTIONS \"\")\n"
    "find_package(OpenCV REQUIRED core imgproc imgcodecs)\n"
    'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fexceptions -frtti -fopenmp -Os")\n'
    "if(DEFINED ANDROID_NDK_MAJOR AND ${ANDROID_NDK_MAJOR} GREATER 20)\n"
    '    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -static-openmp")\n'
    "endif()\n"
    "add_executable(colorize-ncnn main.cpp colorize_impl.cpp)\n"
    'set_source_files_properties(colorize_impl.cpp PROPERTIES COMPILE_FLAGS "-fno-rtti")\n'
    "target_link_libraries(colorize-ncnn ncnn ${OpenCV_LIBS})\n"
)
open("colorize-src/CMakeLists.txt","w").write(cmake)

impl = (
    "#include <cstdio>\n"
    "#include <cstring>\n"
    "#include <string>\n"
    "#include <net.h>\n"
    "#include <layer.h>\n"
    "class Sig17Slice : public ncnn::Layer {\n"
    "public:\n"
    "    Sig17Slice() { one_blob_only = true; }\n"
    "    int forward(const ncnn::Mat& b, ncnn::Mat& t, const ncnn::Option& opt) const override {\n"
    "        int w=b.w,h=b.h,c=b.c,ow=w/2,oh=h/2;\n"
    "        t.create(ow,oh,c,4u,1,opt.blob_allocator);\n"
    "        if(t.empty())return -100;\n"
    "        for(int p=0;p<c;p++){\n"
    "            const float* ptr=b.channel(p%c).row((p/c)%2)+((p/c)/2);\n"
    "            float* o=t.channel(p);\n"
    "            for(int i=0;i<oh;i++){for(int j=0;j<ow;j++){*o++=*ptr;ptr+=2;}ptr+=w;}\n"
    "        }\n"
    "        return 0;\n"
    "    }\n"
    "};\n"
    "DEFINE_LAYER_CREATOR(Sig17Slice)\n"
    'extern "C" int colorize_run(const float* L256, float* ab_out, const char* model_dir) {\n'
    "    ncnn::Net net;\n"
    "    net.opt.use_vulkan_compute=false;\n"
    "    net.opt.num_threads=2;\n"
    '    net.register_custom_layer("Sig17Slice",Sig17Slice_layer_creator);\n'
    "    std::string mp(model_dir);\n"
    '    if(net.load_param((mp+"/siggraph17_color_sim.param").c_str()))return -1;\n'
    '    if(net.load_model((mp+"/siggraph17_color_sim.bin").c_str()))return -1;\n'
    "    ncnn::Mat in(256,256,1,(void*)L256); in=in.clone();\n"
    "    ncnn::Extractor ex=net.create_extractor();\n"
    '    ex.input("input",in); ncnn::Mat out; ex.extract("out_ab",out);\n'
    "    if(out.empty())return -2;\n"
    "    int n=out.w*out.h;\n"
    "    memcpy(ab_out,out.data,n*sizeof(float));\n"
    "    memcpy(ab_out+n,(float*)out.data+n,n*sizeof(float));\n"
    "    ab_out[n*2]=(float)out.w; ab_out[n*2+1]=(float)out.h;\n"
    "    return 0;\n"
    "}\n"
)
open("colorize-src/colorize_impl.cpp","w").write(impl)

# main.cpp with saturation boost + vibrance post-processing
main = r"""
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <cmath>
#include <opencv2/opencv.hpp>
extern "C" int colorize_run(const float* L256, float* ab_out, const char* model_dir);

// Boost saturation and vibrance of the colourised result
// sat_scale: multiplier for a/b channels (1.4 = +40% saturation)
// vibrance:  extra boost for less-saturated pixels (makes muted colours vivid)
static void enhance_colour(cv::Mat& lab_f, float sat_scale, float vibrance) {
    for (int y = 0; y < lab_f.rows; y++) {
        for (int x = 0; x < lab_f.cols; x++) {
            cv::Vec3f& p = lab_f.at<cv::Vec3f>(y, x);
            float a = p[1], b = p[2];
            // Current saturation (chroma)
            float chroma = std::sqrt(a*a + b*b);
            // Vibrance: boost low-saturation pixels more
            float vib_boost = 1.0f + vibrance * (1.0f - std::min(chroma / 60.0f, 1.0f));
            float scale = sat_scale * vib_boost;
            p[1] = std::max(-127.f, std::min(127.f, a * scale));
            p[2] = std::max(-127.f, std::min(127.f, b * scale));
        }
    }
}

int main(int argc, char** argv) {
    std::string input, output, model_dir;
    bool verbose = false;
    float sat   = 1.5f;  // saturation boost (1.0 = no change)
    float vib   = 0.4f;  // vibrance boost

    for (int i = 1; i < argc; i++) {
        if      (!strcmp(argv[i],"-i") && i+1<argc) input     = argv[++i];
        else if (!strcmp(argv[i],"-o") && i+1<argc) output    = argv[++i];
        else if (!strcmp(argv[i],"-m") && i+1<argc) model_dir = argv[++i];
        else if (!strcmp(argv[i],"-v"))              verbose   = true;
        else if (!strcmp(argv[i],"-s") && i+1<argc) sat       = atof(argv[++i]);
        else if (!strcmp(argv[i],"-b") && i+1<argc) vib       = atof(argv[++i]);
    }
    if (input.empty() || output.empty() || model_dir.empty()) {
        fprintf(stderr, "Usage: colorize-ncnn -i input -o output -m model_dir [-s sat] [-b vib]\n");
        return 1;
    }

    cv::Mat bgr = cv::imread(input, cv::IMREAD_COLOR);
    if (bgr.empty()) { fprintf(stderr, "failed to read %s\n", input.c_str()); return 1; }
    if (verbose) fprintf(stderr, "input: %dx%d\n", bgr.cols, bgr.rows);

    cv::Mat base; bgr.convertTo(base, CV_32F, 1.0/255.0);
    cv::Mat lab; cvtColor(base, lab, cv::COLOR_BGR2Lab);
    cv::Mat L; cv::extractChannel(lab, L, 0);
    cv::Mat L256; cv::resize(L, L256, cv::Size(256,256));

    const int MAX = 256*256;
    std::vector<float> ab(MAX*2+2, 0.f);
    int ret = colorize_run((const float*)L256.data, ab.data(), model_dir.c_str());
    if (ret < 0) { fprintf(stderr, "inference failed %d\n", ret); return 1; }

    int nw = (int)ab[MAX*2], nh = (int)ab[MAX*2+1], np = nw*nh;
    cv::Mat a(nh, nw, CV_32F, ab.data());
    cv::Mat b2(nh, nw, CV_32F, ab.data()+np);
    cv::resize(a,  a,  bgr.size());
    cv::resize(b2, b2, bgr.size());

    // Merge into LAB float image
    cv::Mat chn[] = {L, a, b2};
    cv::Mat lab_out;
    cv::merge(chn, 3, lab_out);

    // ── Post-processing: saturation + vibrance boost ──────────────────
    enhance_colour(lab_out, sat, vib);

    // Convert back to BGR
    cv::Mat color; cvtColor(lab_out, color, cv::COLOR_Lab2BGR);

    // Slight contrast enhancement (CLAHE on L channel)
    cv::Mat color_u8; color.convertTo(color_u8, CV_8UC3, 255.0);
    cv::Mat yuv; cvtColor(color_u8, yuv, cv::COLOR_BGR2YCrCb);
    std::vector<cv::Mat> yuv_ch;
    cv::split(yuv, yuv_ch);
    cv::Ptr<cv::CLAHE> clahe = cv::createCLAHE(1.5, cv::Size(8,8));
    clahe->apply(yuv_ch[0], yuv_ch[0]);
    cv::merge(yuv_ch, yuv);
    cv::Mat out_final; cvtColor(yuv, out_final, cv::COLOR_YCrCb2BGR);

    if (!cv::imwrite(output, out_final)) {
        fprintf(stderr, "write failed %s\n", output.c_str()); return 1;
    }
    if (verbose) fprintf(stderr, "saved %s\n", output.c_str());
    return 0;
}
"""
open("colorize-src/main.cpp","w").write(main)

print("colorize-src generated OK")
