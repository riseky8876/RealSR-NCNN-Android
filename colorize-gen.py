#!/usr/bin/env python3
"""Generates colorize-ncnn C++ sources into colorize-src/"""
import sys, os

# Convert to absolute paths — CMake requires absolute paths for *_DIR variables
ncnn_dir   = os.path.abspath(sys.argv[1])
opencv_dir = os.path.abspath(sys.argv[2])

os.makedirs("colorize-src", exist_ok=True)

print(f"ncnn_DIR  (abs): {ncnn_dir}")
print(f"opencv_DIR (abs): {opencv_dir}")

# Verify the config files actually exist
ncnn_cfg   = os.path.join(ncnn_dir,   "ncnnConfig.cmake")
opencv_cfg = os.path.join(opencv_dir, "OpenCVConfig.cmake")
if not os.path.exists(ncnn_cfg):
    print(f"ERROR: {ncnn_cfg} not found!", file=sys.stderr); sys.exit(1)
if not os.path.exists(opencv_cfg):
    print(f"ERROR: {opencv_cfg} not found!", file=sys.stderr); sys.exit(1)

# ── CMakeLists.txt ────────────────────────────────────────────────────────────
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

# ── colorize_impl.cpp ─────────────────────────────────────────────────────────
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

# ── main.cpp ──────────────────────────────────────────────────────────────────
main = (
    "#include <cstdio>\n"
    "#include <cstring>\n"
    "#include <string>\n"
    "#include <vector>\n"
    "#include <opencv2/opencv.hpp>\n"
    'extern "C" int colorize_run(const float* L256, float* ab_out, const char* model_dir);\n'
    "int main(int argc, char** argv) {\n"
    "    std::string input,output,model_dir; bool verbose=false;\n"
    "    for(int i=1;i<argc;i++){\n"
    '        if(!strcmp(argv[i],"-i")&&i+1<argc)input=argv[++i];\n'
    '        else if(!strcmp(argv[i],"-o")&&i+1<argc)output=argv[++i];\n'
    '        else if(!strcmp(argv[i],"-m")&&i+1<argc)model_dir=argv[++i];\n'
    '        else if(!strcmp(argv[i],"-v"))verbose=true;\n'
    "    }\n"
    "    if(input.empty()||output.empty()||model_dir.empty()){\n"
    '        fprintf(stderr,"Usage: colorize-ncnn -i input -o output -m model_dir\\n");return 1;}\n'
    "    cv::Mat bgr=cv::imread(input,cv::IMREAD_COLOR);\n"
    '    if(bgr.empty()){fprintf(stderr,"failed to read input\\n");return 1;}\n'
    "    cv::Mat base; bgr.convertTo(base,CV_32F,1.0/255.0);\n"
    "    cv::Mat lab; cvtColor(base,lab,cv::COLOR_BGR2Lab);\n"
    "    cv::Mat L; cv::extractChannel(lab,L,0);\n"
    "    cv::Mat L256; cv::resize(L,L256,cv::Size(256,256));\n"
    "    const int MAX=256*256;\n"
    "    std::vector<float> ab(MAX*2+2,0.f);\n"
    "    int ret=colorize_run((const float*)L256.data,ab.data(),model_dir.c_str());\n"
    '    if(ret<0){fprintf(stderr,"inference failed %d\\n",ret);return 1;}\n'
    "    int nw=(int)ab[MAX*2],nh=(int)ab[MAX*2+1],np=nw*nh;\n"
    "    cv::Mat a(nh,nw,CV_32F,ab.data()),b2(nh,nw,CV_32F,ab.data()+np);\n"
    "    cv::resize(a,a,bgr.size()); cv::resize(b2,b2,bgr.size());\n"
    "    cv::Mat chn[]={L,a,b2},lo; cv::merge(chn,3,lo);\n"
    "    cv::Mat color; cvtColor(lo,color,cv::COLOR_Lab2BGR);\n"
    "    cv::Mat out8; color.convertTo(out8,CV_8UC3,255.0);\n"
    '    if(!cv::imwrite(output,out8)){fprintf(stderr,"write failed\\n");return 1;}\n'
    '    if(verbose)fprintf(stderr,"saved %s\\n",output.c_str());\n'
    "    return 0;\n"
    "}\n"
)
open("colorize-src/main.cpp","w").write(main)

print("colorize-src generated OK")
