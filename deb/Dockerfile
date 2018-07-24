FROM debian:9

RUN apt-get update
RUN apt-get install -y \
    build-essential vim cscope \
    curl wget manpages manpages-zh

# setup bash
COPY ./bashrc ~/.bashrc
COPY ./bash_aliases ~/.bash_aliases

# setup vim configuration
RUN curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
COPY ./vimrc ~/.vimrc
RUN vim -c "PlugInstall" -c "qa"




CMD "bash"
