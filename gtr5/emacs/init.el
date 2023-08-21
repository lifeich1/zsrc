;; (add-to-list 'load-path "~/.emacs.d/modes")

;; (autoload 'markdown-mode "markdown-mode"
;;  "Major mode for editing Markdown files" t)

;(add-to-list 'auto-mode-alist '("\\.sol\\'" . solidity-mode))

(add-hook 'emacs-lisp-mode-hook 'show-paren-mode)

(require 'package)
;(add-to-list 'package-archives
;	     '("melpa" . "http://melpa.milkbox.net/packages/")
					;	     t)
(setq package-archives
      '(("gun" . "http://mirrors.tuna.tsinghua.edu.cn/elpa/gnu/")
	("melpa" . "http://mirrors.tuna.tsinghua.edu.cn/elpa/melpa/")))
(package-initialize)



(when (memq window-system '(mac ns x))
  (exec-path-from-shell-initialize))

(if (eq system-type 'darwin) 
  (progn 
    (set-language-environment 'UTF-8)
    (set-locale-environment "UTF-8")
    (set-default-font "Menlo 16")
  )
)

(global-set-key "\C-cl" 'org-store-link)
(global-set-key "\C-ca" 'org-agenda)
(global-set-key "\C-cc" 'org-capture)
(global-set-key "\C-cb" 'org-switchb)

(setq ring-bell-function 'ignore)




(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(easy-jekyll-basedir "/home/fool/Code/hub/lifeich1.github.io")
 '(easy-jekyll-postdir "_posts")
 '(easy-jekyll-url "https://lifeich1.github.io/")
 '(org-agenda-custom-commands
   '(("n" "Agenda and all TODOs"
      ((agenda "" nil)
       (alltodo "" nil))
      nil)
     ("w" "weekly report"
      ((tags "TIMESTAMP_IA>=\"<-1w>\"/DONE"
	     ((org-agenda-sorting-strategy
	       '(tag-up)))))
      nil
      ("test.html"))))
 '(org-agenda-files
   '("~/Document/practise/mfk-yn.org" "~/Document/diend/memo/books-going-to-lend.org" "~/Document/practise/record.org"))
 '(org-agenda-span 10)
 '(org-agenda-todo-ignore-scheduled nil)
 '(org-habit-show-all-today t)
 '(org-habit-show-habits-only-for-today t)
 '(org-modules
   '(org-bbdb org-bibtex org-docview org-gnus org-habit org-info org-irc org-mhe org-rmail org-w3m))
 '(package-selected-packages '(exec-path-from-shell easy-jekyll markdown-mode))
 '(show-paren-mode t)
 '(truncate-lines t))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(default ((t (:family "Ubuntu Mono" :foundry "DAMA" :slant normal :weight normal :height 157 :width normal)))))

(setq org-agenda-start-day "-3d")
