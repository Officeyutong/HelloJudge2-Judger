#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <inttypes.h>
#include <signal.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
#include <utility>
#include <vector>
namespace docker_watcher {
using std::cin;
using std::cout;
using std::endl;
using pair_t = std::pair<int64_t, int64_t>;
int64_t get_current_usec() {
    timeval curr;
    gettimeofday(&curr, nullptr);
    return curr.tv_sec * 1000000 + curr.tv_usec;
};
void my_string_split(const std::string& str,
                     const char* token,
                     std::vector<std::string>& result) {
    char* buf = new char[str.length() + 1];
    strcpy(buf, str.c_str());
    char* sec = strtok(buf, token);
    while (sec != nullptr) {
        result.push_back(std::string(sec));
        sec = strtok(NULL, token);
    }
    delete[] buf;
}
std::string my_string_format(const char* format, const std::string& val) {
    char* buf = new char[strlen(format) + val.length()];
    sprintf(buf, format, val.c_str());
    auto ret = std::string(buf);
    delete[] buf;
    return ret;
}

pair_t watch(int pid, int time_limit) {
    std::string memory, cpu;
    static char buf[1024];
    sprintf(buf, "/proc/%d/cgroup", pid);
    auto fp = fopen(buf, "r");
    if (!fp) {
        return pair_t(0, 0);
    }
    while (fgets(buf, 1024, fp)) {
        std::vector<std::string> result;
        std::string str = buf;
        while (isspace(str.back()))
            str.pop_back();
        my_string_split(str, ":", result);
        if (result.size() == 3) {
            if (strstr(result[1].c_str(), "cpu")) {
                cpu = my_string_format("/sys/fs/cgroup/cpu%s/cpu.stat",
                                       result[2]);
            }
            else if (strstr(result[1].c_str(), "memory")) {
                memory = my_string_format(
                    "/sys/fs/cgroup/memory%s/memory.usage_in_bytes", result[2]);
            }
        }
    }
    // cout << "cpu = " << cpu << " mem = " << memory << endl;
    auto begin = get_current_usec();
    int64_t time_result = -1;
    int64_t total_memory_cost = 0, memory_cost_count = 0;
    while (!kill(pid, 0)) {
        time_result = get_current_usec() - begin;
        if (time_result >= time_limit * 1000) {
            break;
        }
        auto fp = fopen(memory.c_str(), "r");
        if (fp) {
            int64_t curr;
            if (fscanf(fp, "%" SCNd64, &curr) > 0) {
                total_memory_cost += curr, memory_cost_count += 1;
            }
            fclose(fp);
        } else
            break;

        usleep(100);
    }
    int64_t memory_result;
    if (memory_cost_count == 0)
        memory_result = 0;
    else
        memory_result = total_memory_cost / memory_cost_count;
    if (time_result == -1)
        time_result = 0;
    fclose(fp);
    return pair_t(time_result / 1000, memory_result);
}
}  // namespace docker_watcher
// #ifdef DEBUG
// int main() {
//     using namespace docker_watcher;
//     cout << my_string_format("/sys/fs/cgroup/memory%s/memory.usage_in_bytes",
//                              "[string]")
//          << endl;
//     // std::vector<std::string> result;
//     // my_string_split("aaaa:b:cccc:d:", ":", result);
//     // for (const auto& val : result) {
//     //     cout << val << endl;
//     // }
//     return 0;
// }
// #else
static PyObject* docker_watcher_watch(PyObject* self, PyObject* args) {
    int pid, time_limit;
    if (!PyArg_ParseTuple(args, "ii", &pid, &time_limit)) {
        return NULL;
    }
    auto result = docker_watcher::watch(pid, time_limit);
    return Py_BuildValue("LL", result.first, result.second);
}

static PyMethodDef DockerWatcherMethods[] = {
    {.ml_name = "watch",
     .ml_meth = docker_watcher_watch,
     .ml_flags = METH_VARARGS,
     .ml_doc = "Watah a process, return its execution time and memory"},
    {NULL, NULL, 0, NULL}};
static PyModuleDef DockerWatcherModule = {.m_base = PyModuleDef_HEAD_INIT,
                                          .m_name = "docker_watcher",
                                          .m_doc = NULL,
                                          .m_size = -1,
                                          .m_methods = DockerWatcherMethods};

PyMODINIT_FUNC PyInit_docker_watcher(void) {
    return PyModule_Create(&DockerWatcherModule);
}
// #endif