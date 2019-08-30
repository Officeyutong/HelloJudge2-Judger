#include <inttypes.h>
#include <signal.h>
#include <sys/time.h>
#include <sys/types.h>
#include <boost/algorithm/string.hpp>
#include <boost/format.hpp>
#include <boost/python.hpp>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
using namespace boost;
using algorithm::split;
using boost::format;
using std::cin;
using std::cout;
using std::endl;
int64_t get_current_usec() {
    timeval curr;
    gettimeofday(&curr, nullptr);
    return curr.tv_sec * 1000000 + curr.tv_usec;
};
python::tuple watch(int pid, int time_limit) {
    std::string memory, cpu;
    static char buf[1024];
    sprintf(buf, "/proc/%d/cgroup", pid);
    auto fp = fopen(buf, "r");
    if (!fp) {
        return python::make_tuple(0, 0);
    }
    while (fgets(buf, 1024, fp)) {
        std::vector<std::string> result;
        std::string str = buf;
        while (isspace(str.back())) str.pop_back();
        split(result, str, boost::is_any_of(":"), boost::token_compress_on);
        if (result.size() == 3) {
            if (strstr(result[1].c_str(), "cpu"))
                cpu =
                    (format("/sys/fs/cgroup/cpu%s/cpu.stat") % result[2]).str();
            else if (strcmp(result[1].c_str(), "memory"))
                memory =
                    (format("/sys/fs/cgroup/memory%s/memory.usage_in_bytes") %
                     result[2])
                        .str();
        }
    }
    auto begin = get_current_usec();
    int64_t time_result = -1;
    // time_limit *= 1000;
    // const auto memory_file_ptr = memory.c_str();
    int64_t total_memory_cost = 0, memory_cost_count = 0;
    while (!kill(pid, 0)) {
        auto fp = fopen(memory.c_str(), "r");
        if (fp) {
            int64_t curr;
            if (fscanf(fp, "%" SCNd64, &curr) > 0) {
                // memory_result = curr;
                total_memory_cost += curr, memory_cost_count += 1;
            }
            fclose(fp);
        } else
            break;
        time_result = get_current_usec() - begin;
        if (time_result >= time_limit * 1000) {
            break;
        }
        usleep(100);
    }
    int64_t memory_result;
    if (memory_cost_count == 0)
        memory_result = 0;
    else
        memory_result = total_memory_cost / memory_cost_count;
    if (time_result == -1) time_result = 0;
    fclose(fp);
    return python::make_tuple(time_result / 1000, memory_result);
}

BOOST_PYTHON_MODULE(docker_watcher) {
    using namespace boost::python;
    def("watch", watch);
}