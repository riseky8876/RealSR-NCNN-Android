// colorize-ncnn main.cpp
// Usage: colorize-ncnn -i input.jpg -o output.jpg -m model_dir
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <opencv2/opencv.hpp>

extern "C" int colorize_image(const float* L_256, float* ab_out, const char* model_dir);

static void print_usage(const char* prog) {
    fprintf(stderr,
        "Usage: %s -i input -o output -m model_dir\n"
        "  -i  input image path (jpg/png)\n"
        "  -o  output image path (jpg/png)\n"
        "  -m  model directory containing siggraph17_color_sim.param/.bin\n"
        "  -v  verbose\n", prog);
}

int main(int argc, char** argv) {
    std::string input_path, output_path, model_dir;
    bool verbose = false;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-i") && i+1 < argc) input_path  = argv[++i];
        else if (!strcmp(argv[i], "-o") && i+1 < argc) output_path = argv[++i];
        else if (!strcmp(argv[i], "-m") && i+1 < argc) model_dir   = argv[++i];
        else if (!strcmp(argv[i], "-v")) verbose = true;
        else if (!strcmp(argv[i], "-h")) { print_usage(argv[0]); return 0; }
    }

    if (input_path.empty() || output_path.empty() || model_dir.empty()) {
        print_usage(argv[0]); return 1;
    }

    if (verbose) fprintf(stderr, "colorize-ncnn: input=%s\n", input_path.c_str());

    cv::Mat bgr = cv::imread(input_path, cv::IMREAD_COLOR);
    if (bgr.empty()) {
        fprintf(stderr, "colorize-ncnn: failed to read %s\n", input_path.c_str());
        return 1;
    }
    if (verbose) fprintf(stderr, "colorize-ncnn: image %dx%d\n", bgr.cols, bgr.rows);

    // BGR -> LAB, extract L, resize to 256x256
    cv::Mat base;
    bgr.convertTo(base, CV_32F, 1.0/255.0);
    cv::Mat lab;
    cvtColor(base, lab, cv::COLOR_BGR2Lab);
    cv::Mat L;
    cv::extractChannel(lab, L, 0);
    cv::Mat L256;
    cv::resize(L, L256, cv::Size(256,256));

    // Run ncnn colorization
    const int MAX = 256*256;
    std::vector<float> ab_buf(MAX*2 + 2, 0.f);
    int ret = colorize_image((const float*)L256.data, ab_buf.data(), model_dir.c_str());
    if (ret < 0) {
        fprintf(stderr, "colorize-ncnn: inference failed (%d)\n", ret);
        return 1;
    }

    int ncnn_w = (int)ab_buf[MAX*2];
    int ncnn_h = (int)ab_buf[MAX*2+1];
    if (verbose) fprintf(stderr, "colorize-ncnn: ncnn output %dx%d\n", ncnn_w, ncnn_h);

    int np = ncnn_w * ncnn_h;
    cv::Mat a(ncnn_h, ncnn_w, CV_32F, ab_buf.data());
    cv::Mat b(ncnn_h, ncnn_w, CV_32F, ab_buf.data() + np);
    cv::resize(a, a, bgr.size());
    cv::resize(b, b, bgr.size());

    cv::Mat chn[] = {L, a, b};
    cv::Mat lab_out;
    cv::merge(chn, 3, lab_out);
    cv::Mat color;
    cvtColor(lab_out, color, cv::COLOR_Lab2BGR);
    cv::Mat out_u8;
    color.convertTo(out_u8, CV_8UC3, 255.0);

    if (!cv::imwrite(output_path, out_u8)) {
        fprintf(stderr, "colorize-ncnn: failed to write %s\n", output_path.c_str());
        return 1;
    }
    if (verbose) fprintf(stderr, "colorize-ncnn: saved to %s\n", output_path.c_str());
    return 0;
}
