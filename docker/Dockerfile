FROM ubuntu:19.04

# RUN sed -i 's/archive.ubuntu.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list
# RUN sed -i 's/security.ubuntu.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list
RUN apt update && apt install g++ -y && apt install python2.7 -y && apt install python3.7 -y && apt install openjdk-8-jdk -y
RUN apt install haskell-platform -y
RUN apt-get install curl build-essential m4 zlib1g-dev libssl-dev ocaml ocaml-native-compilers opam -y
RUN apt install rustc -y
RUN apt install git
RUN git clone https://github.com/samshadwell/TrumpScript.git /root/TrumpScript
RUN sh -c "echo \"export PATH=$PATH:/root/TrumpScript/bin\" >> /root/.bashrc"