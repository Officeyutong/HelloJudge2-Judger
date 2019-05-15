#include <inttypes.h>
#include <sys/time.h>
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
    char buf[1024];
    sprintf(buf, "/proc/%d/cgroup", pid);
    auto fp = fopen(buf, "r");
    // cout << "Watching pid " << pid << endl;
    if (!fp) {
        // cout << "Error: " << errno << endl;
        return python::make_tuple(0, 0);
    }
    while (fgets(buf, 1024, fp)) {
        // cout<<id<<" "<<type<<" "<<path<<endl;
        std::vector<std::string> result;
        std::string str = buf;
        while (isspace(str.back())) str.pop_back();
        split(result, str, boost::is_any_of(":"), boost::token_compress_on);
        // for (auto x : result) cout << x << " ";
        // cout << endl;
        if (result.size() == 3) {
            if (strstr(result[1].c_str(), "cpu"))
                cpu =
                    (format("/sys/fs/cgroup/cpu%s/cpu.stat") % result[2]).str();
            else if (strcmp(result[1].c_str(), "memory"))
                memory =
                    (format(
                         "/sys/fs/cgroup/memory%s/memory.max_usage_in_bytes") %
                     result[2])
                        .str();
        }
    }
    fclose(fp);
    // cout << "memory file = " << memory << endl << " cpu file = " << cpu << endl;
    auto begin = get_current_usec();
    int64_t memory_result = -1, time_result = -1;
    while (true) {
        auto fp = fopen(memory.c_str(), "r");
        if (fp) {
            int64_t curr;
            if (fscanf(fp, "%" SCNd64, &curr) > 0) {
                memory_result = curr;
                fclose(fp);
            } else {
                break;
            }

        } else {
            break;
        }
        time_result = get_current_usec() - begin;
        if (time_result >= time_limit * 1000) {
            break;
        }
    }
    if (memory_result == -1) memory_result = 0;
    if (time_result == -1) time_result = 0;

    return python::make_tuple(time_result / 1000, memory_result);
}

BOOST_PYTHON_MODULE(docker_watcher) {
    using namespace boost::python;
    def("watch", watch);
}