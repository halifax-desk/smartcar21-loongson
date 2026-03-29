#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <dirent.h>
#include <windows.h>

#define BINARY_THRESHOLD 128
#define MAX_EDGE_POINTS 10000
#define MAX_FILES 1000

typedef struct {
    int width;
    int height;
    uint8_t* data;
} image_t;

typedef struct {
    int row;
    int col;
    int side;
} edge_point_t;

static int USER_IMAGE_WIDTH = 0;
static int USER_IMAGE_HEIGHT = 0;
static int Image_Centre = 0;
static uint8_t Frame_Number = 1;
static edge_point_t Road_Edge[MAX_EDGE_POINTS];
static int Edge_Point_Count = 0;

void Image_Binary(image_t* img) {
    printf("开始二值化图像...\n");
    printf("二值化阈值: %d (像素值 >= %d 为白色, < %d 为黑色)\n", BINARY_THRESHOLD, BINARY_THRESHOLD, BINARY_THRESHOLD);
    
    for (int i = 0; i < img->width * img->height; i++) {
        if (img->data[i] >= BINARY_THRESHOLD) {
            img->data[i] = 255;
        } else {
            img->data[i] = 0;
        }
    }
    printf("二值化完成\n");
}

int Read_Image(const char* filename, image_t* img) {
    FILE* fp = fopen(filename, "rb");
    if (!fp) {
        printf("错误: 无法打开图像文件 %s\n", filename);
        return -1;
    }

    fread(&img->width, sizeof(int), 1, fp);
    fread(&img->height, sizeof(int), 1, fp);

    USER_IMAGE_WIDTH = img->width;
    USER_IMAGE_HEIGHT = img->height;

    img->data = (uint8_t*)malloc(img->width * img->height * sizeof(uint8_t));
    if (!img->data) {
        printf("错误: 内存分配失败\n");
        fclose(fp);
        return -1;
    }

    size_t total_pixels = img->width * img->height;
    size_t read_count = fread(img->data, sizeof(uint8_t), total_pixels, fp);
    if (read_count != total_pixels) {
        printf("错误: 图像数据读取不完整\n");
        free(img->data);
        fclose(fp);
        return -1;
    }

    fclose(fp);

    Image_Centre = USER_IMAGE_WIDTH / 2;
    printf("图像读取成功: %dx%d, 中心列: %d\n", USER_IMAGE_WIDTH, USER_IMAGE_HEIGHT, Image_Centre);

    return 0;
}

void Get_Road_Edge(image_t* img) {
    printf("开始检测道路边缘...\n");
    printf("检测策略: 从图像底部向上逐行扫描，从中心向两侧寻找第一个黑色像素点\n");
    Edge_Point_Count = 0;

    for (int row = img->height - 1; row >= 0; row--) {
        for (int col = Image_Centre; col < img->width; col++) {
            int pixel_index = row * img->width + col;
            if (img->data[pixel_index] == 0) {
                if (Edge_Point_Count < MAX_EDGE_POINTS) {
                    Road_Edge[Edge_Point_Count].row = row;
                    Road_Edge[Edge_Point_Count].col = col;
                    Road_Edge[Edge_Point_Count].side = 1;
                    Edge_Point_Count++;
                }
                break;
            }
        }

        for (int col = Image_Centre - 1; col >= 0; col--) {
            int pixel_index = row * img->width + col;
            if (img->data[pixel_index] == 0) {
                if (Edge_Point_Count < MAX_EDGE_POINTS) {
                    Road_Edge[Edge_Point_Count].row = row;
                    Road_Edge[Edge_Point_Count].col = col;
                    Road_Edge[Edge_Point_Count].side = -1;
                    Edge_Point_Count++;
                }
                break;
            }
        }
    }

    printf("道路边缘检测完成，共找到 %d 个边缘点\n", Edge_Point_Count);
}

void Print_Edge_Statistics() {
    int left_count = 0;
    int right_count = 0;
    int left_sum = 0;
    int right_sum = 0;

    for (int i = 0; i < Edge_Point_Count; i++) {
        if (Road_Edge[i].side == -1) {
            left_count++;
            left_sum += Road_Edge[i].col;
        } else if (Road_Edge[i].side == 1) {
            right_count++;
            right_sum += Road_Edge[i].col;
        }
    }

    printf("\n=== 边缘统计信息 ===\n");
    printf("左侧边缘点数: %d, 平均列位置: %.2f\n", left_count, left_count > 0 ? (float)left_sum / left_count : 0);
    printf("右侧边缘点数: %d, 平均列位置: %.2f\n", right_count, right_count > 0 ? (float)right_sum / right_count : 0);
    printf("总边缘点数: %d\n", Edge_Point_Count);
    printf("===================\n\n");
}

void Save_Edge_Coordinates(const char* filename) {
    FILE* fp = fopen(filename, "w");
    if (!fp) {
        printf("错误: 无法创建坐标文件 %s\n", filename);
        return;
    }

    fprintf(fp, "Frame_Number,%d\n", Frame_Number);
    fprintf(fp, "Image_Width,%d\n", USER_IMAGE_WIDTH);
    fprintf(fp, "Image_Height,%d\n", USER_IMAGE_HEIGHT);
    fprintf(fp, "Image_Centre,%d\n", Image_Centre);
    fprintf(fp, "Total_Edge_Points,%d\n", Edge_Point_Count);
    fprintf(fp, "\n");

    fprintf(fp, "Index,Row,Col,Side\n");
    for (int i = 0; i < Edge_Point_Count; i++) {
        fprintf(fp, "%d,%d,%d,%d\n", i, Road_Edge[i].row, Road_Edge[i].col, Road_Edge[i].side);
    }

    fclose(fp);
    printf("边缘点坐标已保存到 %s\n", filename);
}

void Free_Image(image_t* img) {
    if (img->data) {
        free(img->data);
        img->data = NULL;
    }
}

int Get_Image_Files(const char* dir_path, char files[][256], int* count) {
    DIR* dir = opendir(dir_path);
    if (!dir) {
        printf("警告: 无法打开目录 %s\n", dir_path);
        return -1;
    }

    struct dirent* entry;
    *count = 0;

    while ((entry = readdir(dir)) != NULL && *count < MAX_FILES) {
        if (strstr(entry->d_name, ".img") != NULL || strstr(entry->d_name, ".png") != NULL || strstr(entry->d_name, ".jpg") != NULL) {
            strcpy(files[*count], entry->d_name);
            (*count)++;
        }
    }

    closedir(dir);
    return 0;
}

void Create_Directory(const char* path) {
    #ifdef _WIN32
        mkdir(path);
    #else
        mkdir(path, 0777);
    #endif
}

int main(int argc, char* argv[]) {
    SetConsoleOutputCP(65001);
    
    printf("========================================\n");
    printf("    智能车视觉道路边缘检测系统\n");
    printf("========================================\n\n");

    char input_files[MAX_FILES][256];
    int file_count = 0;

    if (Get_Image_Files("img", input_files, &file_count) != 0 || file_count == 0) {
        printf("错误: img目录中没有找到图像文件\n");
        printf("请将图像文件放入img目录中\n");
        return 1;
    }

    printf("找到 %d 个图像文件:\n", file_count);
    for (int i = 0; i < file_count; i++) {
        printf("  [%d] %s\n", i + 1, input_files[i]);
    }
    printf("\n");

    Create_Directory("Export");

    for (int i = 0; i < file_count; i++) {
        printf("\n========================================\n");
        printf("处理文件 [%d/%d]: %s\n", i + 1, file_count, input_files[i]);
        printf("========================================\n");

        char input_path[512];
        sprintf(input_path, "img/%s", input_files[i]);

        image_t img = {0};

        if (Read_Image(input_path, &img) != 0) {
            printf("跳过文件: %s\n", input_files[i]);
            continue;
        }

        Image_Binary(&img);

        Get_Road_Edge(&img);

        Print_Edge_Statistics();

        char coord_filename[512];
        sprintf(coord_filename, "Export/Frame_%03d_coordinates.csv", Frame_Number);
        Save_Edge_Coordinates(coord_filename);

        Frame_Number++;

        Free_Image(&img);

        printf("文件 %s 处理完成\n", input_files[i]);
    }

    printf("\n========================================\n");
    printf("所有文件处理完成！\n");
    printf("共处理 %d 个文件\n", file_count);
    printf("输出目录: Export/\n");
    printf("输出格式: 边缘点坐标 CSV 文件 (Frame_XXX_coordinates.csv)\n");
    printf("========================================\n");

    return 0;
}
