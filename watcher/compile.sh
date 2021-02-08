g++ -shared -o docker_watcher.so -fPIC -I/usr/include/python3.8 docker_watcher.cpp -lpython3.8 -O2 -Wall -Wextra
mv docker_watcher.so ..