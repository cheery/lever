" Vim syntax file
" Language: Lever
" Maintainer: Henri Tuhola
" Latest Revision: December 2015

if exists("b:current_syntax")
    finish
endif

syn keyword leverKeyword if elif else while import from return for in as break continue raise try except
syn keyword leverBoolean true false

syn match   leverNumberError	"\<0[xX]\x*[g-zG-Z]\+\x*[lL]\=\>" display
syn match   leverNumberError	"\<0[oO]\=\o*\D\+\d*[lL]\=\>" display
syn match   leverNumberError	"\<0[bB][01]*\D\+\d*[lL]\=\>" display

syn match   leverNumber	"\<0[xX]\x\+[lL]\=\>" display
syn match   leverNumber "\<0[oO]\o\+[lL]\=\>" display
syn match   leverNumber "\<0[bB][01]\+[lL]\=\>" display

syn match   leverNumberError	"\<\d\+\D[lL]\=\>" display
syn match   leverNumber	"\<\d[lL]\=\>" display
syn match   leverNumber	"\<[0-9]\d\+[lL]\=\>" display
syn match   leverNumber	"\<\d\+[lLjJ]\>" display

syn match   leverNumberError	"\<0[oO]\=\o*[8-9]\d*[lL]\=\>" display
syn match   leverNumberError	"\<0[bB][01]*[2-9]\d*[lL]\=\>" display

syn match   leverNumber		"\.\d\+\%([eE][+-]\=\d\+\)\=[jJ]\=\>" display
syn match   leverNumber		"\<\d\+[eE][+-]\=\d\+[jJ]\=\>" display
syn match   leverNumber		"\<\d\+\.\d*\%([eE][+-]\=\d\+\)\=[jJ]\=" display

syn keyword leverTodo contained TODO FIXME XXX NOTE
syn match leverComment "#.*$" contains=leverTodo

syn region leverString start=+"+ end=+"+ skip=+\\"+
syn region leverString start=+'+ end=+'+ skip=+\\'+

let b:current_syntax = "lever"

hi def link leverTodo        Todo
hi def link leverComment     Comment
hi def link leverKeyword     Statement
hi def link leverHip         Type
hi def link leverString      String
hi def link leverDesc        PreProc
hi def link leverNumber      Constant
hi def link leverBoolean     Boolean
