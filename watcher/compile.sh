g++ -shared -o docker_watcher.so -fPIC -I/usr/include/python3.6m docker_watcher.cpp -lpython3.6m -lboost_python3 -Wall -Wextra -O3
mv docker_watcher.so ..