-- require("nvim-lsp-installer").setup {}
local capabilities = vim.lsp.protocol.make_client_capabilities()
capabilities.textDocument.foldingRange = {
  dynamicRegistration = false,
  lineFoldingOnly = true
}

local lspconfig = require('lspconfig')
---[[
-- vscode extracted
-- lspconfig.jsonls.setup {}
-- lspconfig.html.setup {}
-- lspconfig.cssls.setup {}
--
-- lspconfig.pylsp.setup {}
-- lspconfig.bashls.setup {}
-- lspconfig.eslint.setup {}
-- lspconfig.vimls.setup {}
--]]

lspconfig.nil_ls.setup {
  settings = {
    ['nil'] = {
      formatting = {
        command = { "nixpkgs-fmt" },
      },
    },
  },
}
-- lspconfig.statix.setup {}
-- lspconfig.marksman.setup {}

-- lspconfig.clangd.setup {}
-- lspconfig.perlpls.setup {}
lspconfig.rust_analyzer.setup {
  capabilities = capabilities,
  -- Server-specific settings. See `:help lspconfig-setup`
  settings = {
    ['rust-analyzer'] = {
      cargo = {
        loadOutDirsFromCheck = true,
      },
      procMacro = {
        enable = true,
      },
      check = {
        command = "clippy",
        extraArgs = { "--", "-D", "warnings", "-W", "clippy::pedantic", "-W", "clippy::nursery", "-W", "rust-2018-idioms" },
      },
      -- ["rust-analyzer.cargo.loadOutDirsFromCheck"] = true,
      -- ["rust-analyzer.procMacro.enable"] = true,
      -- ["rust-analyzer.check.command"] = "clippy",
    },
  },
}
lspconfig.lua_ls.setup {
  capabilities = capabilities,
  settings = {
    Lua = {
      runtime = {
        -- Tell the language server which version of Lua you're using (most likely LuaJIT in the case of Neovim)
        version = 'LuaJIT',
      },
      diagnostics = {
        -- Get the language server to recognize the `vim` global
        globals = { 'vim' },
      },
      workspace = {
        -- Make the server aware of Neovim runtime files
        library = vim.api.nvim_get_runtime_file("", true),
        checkThirdParty = false,
      },
      -- Do not send telemetry data containing a randomized but unique identifier
      telemetry = {
        enable = false,
      },
      format = {
        enable = true,
        -- Put format options here
        -- NOTE: the value should be STRING!!
        defaultConfig = {
          indent_style = "space",
          indent_size = "2",
        }
      },
    },
  },
}

-- Global mappings.
-- See `:help vim.diagnostic.*` for documentation on any of the below functions
vim.keymap.set('n', '<Bslash>e', vim.diagnostic.open_float)
vim.keymap.set('n', '[d', vim.diagnostic.goto_prev)
vim.keymap.set('n', ']d', vim.diagnostic.goto_next)
vim.keymap.set('n', '<Bslash>q', vim.diagnostic.setloclist)

-- Use LspAttach autocommand to only map the following keys
-- after the language server attaches to the current buffer
vim.api.nvim_create_autocmd('LspAttach', {
  group = vim.api.nvim_create_augroup('UserLspConfig', {}),
  callback = function(ev)
    local client = vim.lsp.get_client_by_id(ev.data.client_id)
    -- Enable completion triggered by <c-x><c-o>
    vim.bo[ev.buf].omnifunc = 'v:lua.vim.lsp.omnifunc'

    -- Buffer local mappings.
    -- See `:help vim.lsp.*` for documentation on any of the below functions
    local opts = { buffer = ev.buf }
    vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, opts)
    vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
    --vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
    vim.keymap.set('n', '<Bslash>i', vim.lsp.buf.implementation, opts)
    vim.keymap.set('n', '<C-k>', vim.lsp.buf.signature_help, opts)
    vim.keymap.set('n', '<Bslash>wa', vim.lsp.buf.add_workspace_folder, opts)
    vim.keymap.set('n', '<Bslash>wr', vim.lsp.buf.remove_workspace_folder, opts)
    vim.keymap.set('n', '<Bslash>wl', function()
      print(vim.inspect(vim.lsp.buf.list_workspace_folders()))
    end, opts)
    vim.keymap.set('n', '<Bslash>D', vim.lsp.buf.type_definition, opts)
    vim.keymap.set('n', '<Bslash>rn', vim.lsp.buf.rename, opts)
    vim.keymap.set({ 'n', 'v' }, '<Bslash>ca', vim.lsp.buf.code_action, opts)
    vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
    vim.keymap.set('n', '<Bslash>f', function()
      vim.lsp.buf.format { async = true }
    end, opts)

    if client.server_capabilities.documentFormattingProvider then
      vim.api.nvim_create_autocmd('BufWritePre', {
        buffer = ev.buf,
        callback = function()
          vim.lsp.buf.format {}
        end,
      })
    end
  end,
})

require("coverage").setup({
  lang = {
    rust = {
      coverage_command = "cargo run -r -q --package xtask -- coverage --neo",
      project_files_only = false,
    },
  },
})

-- local language_servers = require("lspconfig").util.available_servers() -- or list servers manually like {'gopls', 'clangd'}
local language_servers = {
  'jsonls', 'html', 'cssls', 'pylsp', 'bashls',
  'eslint', 'vimls', 'marksman', 'clangd',
  'perlpls' }
for _, ls in ipairs(language_servers) do
  require('lspconfig')[ls].setup({
    capabilities = capabilities
    -- you can add other fields for setting up lsp server in this table
  })
end
require('ufo').setup({
  preview = {
    win_config = {
      border = { '', '─', '', '', '', '─', '', '' },
      winhighlight = 'Normal:Folded',
      winblend = 0
    },
    mappings = {
      scrollU = '<C-u>',
      scrollD = '<C-d>',
      jumpTop = '[',
      jumpBot = ']'
    }
  },
})

vim.keymap.set('n', 'zR', require('ufo').openAllFolds)
vim.keymap.set('n', 'zM', require('ufo').closeAllFolds)
vim.keymap.set('n', 'zr', require('ufo').openFoldsExceptKinds)
vim.keymap.set('n', 'zm', require('ufo').closeFoldsWith) -- closeAllFolds == closeFoldsWith(0)
vim.keymap.set('n', 'K', function()
  local winid = require('ufo').peekFoldedLinesUnderCursor()
  if not winid then
    -- choose one of coc.nvim and nvim lsp
    vim.lsp.buf.hover()
  end
end)

require("catppuccin").setup({
  flavour = "frappe",
  transparent_background = true,
  term_colors = true,
  highlight_overrides = {
    all = function(colors)
      return {
        StatusLine = { bg = colors.mantle },
        StatusLineNC = { bg = colors.crust },
      }
    end,
  },
})
vim.cmd.colorscheme "catppuccin"
