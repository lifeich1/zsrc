FROM debian:9

ENV HOME=/root

COPY ./apt.list /etc/apt/sources.list
RUN apt-get update

# set locale
RUN apt-get install -y locales
RUN localedef -f UTF-8 -i zh_CN zh_CN.UTF-8 
RUN localedef -f GBK -i zh_CN zh_CN.GBK 
ENV LANG=zh_CN.utf8
ENV LANGUAGE=en:zh_CN
ENV LC_ALL=zh_CN.utf8

# setup bash
COPY ./bashrc $HOME/.bashrc
COPY ./bash_aliases $HOME/.bash_aliases
COPY ./inputrc $HOME/.inputrc

# setup vim configuration
RUN apt-get install -y vim curl git

RUN curl -fLo $HOME/.vim/autoload/plug.vim --create-dirs \
https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

COPY ./vimrc $HOME/.vimrc
RUN vim -c "PlugInstall" -c "qa"

# addtional 
RUN apt-get install -y \
build-essential cscope \
wget man manpages manpages-zh \
exuberant-ctags



CMD "bash"
