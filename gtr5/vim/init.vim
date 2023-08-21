set runtimepath^=~/.vim runtimepath+=~/.vim/after
let &packpath = &runtimepath
source ~/.vimrc

"tmapclear

let g:clipboard = {
      \   'name': 'xsel',
      \   'copy': {
      \      '+': ['xsel', '--nodetach', '-i', '-b'],
      \      '*': ['xsel', '--nodetach', '-i', '-p'],
      \    },
      \   'paste': {
      \      '+': ['xsel', '-o', '-b'],
      \      '*': ['xsel', '-o', '-p'],
      \   },
      \   'cache_enabled': 1,
      \ }

set clipboard+=unnamedplus
tnoremap <Esc> <C-\><C-n>
tnoremap <C-v><Esc> <Esc>
let g:python3_host_prog="/home/fool/opt/miniconda3/bin/python3"
let g:perl_host_prog="/home/fool/opt/perl5/perlbrew/perls/perl-5.34.1/bin/perl"

tnoremap <M-h> <C-\><C-n><C-w><C-h>
tnoremap <M-j> <C-\><C-n><C-w><C-j>
tnoremap <M-k> <C-\><C-n><C-w><C-k>
tnoremap <M-l> <C-\><C-n><C-w><C-l>
tnoremap <M--> <C-\><C-n>gT
tnoremap <M-=> <C-\><C-n>gt
tnoremap <M-_> <C-\><C-n>:-tabmove<CR>
tnoremap <M-+> <C-\><C-n>:+tabmove<CR>

cnoremap <Bslash>at RSPCAutoTest<cr>
cnoremap <Bslash>qt !rm keeptest<cr>

luaf ~/.vim/init.lua
