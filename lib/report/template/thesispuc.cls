%% -*- coding: utf-8; -*-

%%%%
%%%% Copyright (C) 2015 - 2021
%%%% PUC-Rio

%%%% This file is part of ThesisPUC.

%%%% ThesisPUC is free software; you can redistribute it and/or modify
%%%% it under the terms of the GNU General Public License as published
%%%% by the Free Software Foundation; either version 3 of the License,
%%%% or (at your option) any later version.

%%%% ThesisPUC is distributed in the hope that it will be useful, but
%%%% WITHOUT ANY WARRANTY; without even the implied warranty of
%%%% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
%%%% General Public License for more details.

%%%% You should have received a copy of the GNU General Public License
%%%% along with ThesisPUC.  If not, see
%%%% <https://www.gnu.org/licenses/gpl.html>.
%%%%

%%%% ----------------------------------------------------------------------------------
%%%% Versão adaptada para o Relatório de Projeto Final (graduação, DI/PUC-Rio).
%%%% Mantém só o modelo de graduação, conforme o Manual do Aluno: capa e folha de rosto de
%%%% Projeto Final, Arial 11 (Helvetica), espaçamento 1,5, margens 2,5/3,5/2,5/3,5 cm, número
%%%% da página no alto à direita a partir da introdução, resumo e abstract, Referências sem
%%%% numeração. Foram removidos os modelos de dissertação e tese (folha de aprovação,
%%%% ficha catalográfica, dedicatória, duas faces). As opções 'graduacao', 'projetofinal',
%%%% 'msc' e 'phd' são aceitas só para não quebrar um main.tex antigo.
%%%% ----------------------------------------------------------------------------------

\newcommand{\docdate}{}  % See the renewcommands below,
\newcommand{\filedate}{} % these contain the content;-))
\newcommand{\fileversion}{}
\renewcommand{\docdate}{2017/11/12}
\renewcommand{\filedate}{2021/01/25}
\renewcommand{\fileversion}{1.0.11}
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{thesispuc}%
[\filedate\space v\fileversion\space Thesis PUC-Rio document class]


%%%
%%% style options
%%%

%%  booleans
%% \makeatletter
\RequirePackage{ifthen}
\RequirePackage{nth}

% hyphenation
\RequirePackage[main=american,brazilian]{babel}%

\newcommand{\llocale}{brazilian}
\newboolean{puc@localebr}
\setboolean{puc@localebr}{true}
\newboolean{puc@localeus}
\setboolean{puc@localeus}{false}

\newif\if@americanlanguage\@americanlanguagefalse
\DeclareOption{american}%
{
  \@americanlanguagetrue
  \PassOptionsToPackage{main=american}{babel}%
  \setboolean{puc@localeus}{true}%
  \setboolean{puc@localebr}{false}%
  \renewcommand{\llocale}{american}%
}

\newif\if@brazilianlanguage\@brazilianlanguagefalse
\DeclareOption{brazilian}
{
  \@brazilianlanguagetrue
  \PassOptionsToPackage{main=brazilian}{babel}%
  \setboolean{puc@localebr}{true}%
  \setboolean{puc@localeus}{false}%
  \renewcommand{\llocale}{brazilian}%
}

% draft for debugging overful boxes
\newboolean{puc@draft}
\setboolean{puc@draft}{false}
\newif\if@pucdraft\@pucdraftfalse
\DeclareOption{draft}{\@pucdrafttrue\setboolean{puc@draft}{true}}

% Back references
\newif\if@pucbackref\@pucbackreffalse
\DeclareOption{digital}{\@pucbackreftrue}

% Este template é só de graduação (Projeto Final). As opções abaixo existem apenas para que
% um main.tex antigo continue compilando.
\DeclareOption{graduacao}{}
\DeclareOption{projetofinal}{}
\DeclareOption{rascunho}{\setboolean{puc@draft}{true}}

\ProcessOptions\relax


%%%
%%% base style
%%%

\LoadClass[a4paper,11pt\ifpuc@draft,draft\else\fi]{report}
%%\makeatother


%%%
%%% required packages
%%%

% fonts and symbols
\RequirePackage[utf8]{inputenc}
\RequirePackage[T1]{fontenc}             %% OT1 has 127 characters only
\RequirePackage{lmodern}                 %% tex modern font version
% Arial: a Helvetica (Nimbus Sans) tem as mesmas métricas. Como o manual pede Arial em todo
% o texto, a família "romana" também vira Helvetica; a matemática continua em Latin Modern.
\RequirePackage{helvet}
\renewcommand{\rmdefault}{phv}
\RequirePackage{amsfonts}

% Capilatize first letter in words
\RequirePackage{titlecaps}

% graphics inclusion (in particular the PUC logo)
\RequirePackage[pdftex]{graphicx}

% Section titles
\RequirePackage[clearempty, compact]{titlesec}

% table of contents
\RequirePackage[subfigure]{tocloft}

% dynamically change margins
% \RequirePackage{changepage}

% line spacing
\RequirePackage{setspace}

% header and footer
\RequirePackage{fancyhdr}

% front matter inclusion and space in environment
\RequirePackage{atbeginend}

% indent first line of sections and chapters
\RequirePackage{indentfirst}

% number of pages
\RequirePackage{lastpage}

% manipulate strings of tokens
\RequirePackage{xstring}

% Add code support for many programming languages
\RequirePackage{caption} %change listings caption
\RequirePackage{listings}
\RequirePackage{listingsutf8}

% better tables
\RequirePackage{booktabs}

% Manipulate listings layout
\RequirePackage{titletoc}

% Auto add/remove bib,toc,lof and lot in summary
\RequirePackage[nottoc,notlof,notlot]{tocbibind}  % Referências sem numeração

% hyperlink and pdf bookmarks
\RequirePackage[%
  pdftex,%
  colorlinks=true,%
  bookmarksopen=true,%
  breaklinks=true,%
  linkcolor=black,% blue
  anchorcolor=black,%
  citecolor=black,% cyan
  urlcolor=black,% red
  bookmarksnumbered=false%
]{hyperref}

% Algorithm ans algorithms list
\if@americanlanguage
  \RequirePackage[english, onelanguage,ruled,vlined,linesnumbered,commentsnumbered]{algorithm2e}%
\fi
\if@brazilianlanguage
  \RequirePackage[portuguese, onelanguage,ruled,vlined,linesnumbered,commentsnumbered]{algorithm2e}%
\fi

% Back references
\if@pucbackref
  \if@americanlanguage
    \RequirePackage[hyperpageref]{backref}%
    % Usado sem a opção hyperpageref de backref
    \renewcommand{\backrefpagesname}{Cited in page(s):~}
    % Texto padrão antes do número das páginas
    \renewcommand{\backref}{}
    % Define os textos da citação
    \renewcommand*{\backrefalt}[4]{
      \ifcase #1 %
        No citation in the text.%
      \or
        Cited in page #2.%
      \else
        Cited #1 times in pages #2.%
      \fi}%
  \fi
  \if@brazilianlanguage
    \RequirePackage[brazilian,hyperpageref]{backref}%
    % Usado sem a opção hyperpageref de backref
    \renewcommand{\backrefpagesname}{Citado na(s) página(s):~}
    % Texto padrão antes do número das páginas
    \renewcommand{\backref}{}
    % Define os textos da citação
    \renewcommand*{\backrefalt}[4]{
      \ifcase #1 %
        Nenhuma citação no texto.%
      \or
        Citado na página #2.%
      \else
        Citado #1 vezes nas páginas #2.%
      \fi}%
  \fi
\fi

% subfigure loaded here for spacing definition
%\RequirePackage{subfig}
\RequirePackage{subimages}

% List of code settings
\DeclareCaptionFormat{listing}{\rule{\dimexpr\textwidth\relax}{0.4pt}\vspace*{-2.8mm}\\\hspace*{10pt}#1\textbf{:}#2#3}
\lstset{
	basicstyle=\fontsize{9}{11}\ttfamily,
   	numbers=left,
    numberstyle=\tiny,
    numberbychapter=false,
    stepnumber=1,
    numbersep=5pt,
    captionpos=t,
    tabsize=2,
    extendedchars=true,
    mathescape=true,
    breaklines=true,
    keywordstyle=\color{red},
    stringstyle=\color{gray}\ttfamily,
    frame=bt,
    inputencoding=utf8/latin1,
    showspaces=false,
    showtabs=false,
    xleftmargin=10pt,
    framexleftmargin=10pt,
    %framexrightmargin=10pt,
    framexbottommargin=5pt,
    framextopmargin=5pt,
    %backgroundcolor=\color{lightgray},
    showstringspaces=false
}
\captionsetup[lstlisting]{format=listing,singlelinecheck=false, margin=0pt, font={normalsize},labelsep=space,labelfont=bf}

%% \makeatletter


%%%
%%% page layout
%%%

\setlength{\parindent}{1cm}
\setlength{\voffset}{-1in}
\setlength{\topmargin}{1.0cm}   % cabeçalho (número da página) a 1,0 cm do topo
\setlength{\topskip}{0.001cm}
\addtolength{\headheight}{2.5pt}

% Copy of some of the code from the ifmtarg package to save requiring
% ifmtarg
\begingroup
\catcode`\Q=3
\long\gdef\@ifmtarg#1{\@xifmtarg#1QQ\@secondoftwo\@firstoftwo\@nil}
\long\gdef\@xifmtarg#1#2Q#3#4#5\@nil{#4}
\endgroup


% Set the page output parameters
\DeclareRobustCommand{\ch@ngetext}{%
  \setlength{\@colht}{\textheight}\setlength{\@colroom}{\textheight}%
  \setlength{\vsize}{\textheight}\setlength{\columnwidth}{\textwidth}%
  \if@twocolumn%
    \advance\columnwidth-\columnsep \divide\columnwidth\tw@%
    \@firstcolumntrue%
  \fi%
  \setlength{\hsize}{\columnwidth}%
  \setlength{\linewidth}{\hsize}}

%\newcommand{\setpage}[9]{%
\DeclareRobustCommand{\setpage}[9]{%
  \@ifmtarg{#1}{}{\setlength{\textheight}{#1}}%
  \@ifmtarg{#2}{}{\setlength{\textwidth}{#2}}%
  \@ifmtarg{#3}{}{\setlength{\evensidemargin}{#3}}%
  \@ifmtarg{#4}{}{\setlength{\oddsidemargin}{#4}}%
  \@ifmtarg{#5}{}{\setlength{\columnsep}{#5}}%
  \ch@ngetext%
  \@ifmtarg{#6}{}{\setlength{\topmargin}{#6}}%
  \@ifmtarg{#7}{}{\setlength{\headheight}{#7}}%
  \@ifmtarg{#8}{}{\setlength{\headsep}{#8}}%
  \@ifmtarg{#9}{}{\setlength{\footskip}{#9}}%
}

\newcommand{\puc@setallmargins}[5]{%
 % declare length
 \expandafter\newlength\csname puc@topmargin@#1\endcsname%
 \expandafter\newlength\csname puc@bottommargin@#1\endcsname%
 \expandafter\newlength\csname puc@leftmargin@#1\endcsname%
 \expandafter\newlength\csname puc@rightmargin@#1\endcsname%
 \expandafter\newlength\csname puc@textwidth@#1\endcsname%
 \expandafter\newlength\csname puc@oddsidemargin@#1\endcsname%
 \expandafter\newlength\csname puc@evensidemargin@#1\endcsname%
 \expandafter\newlength\csname puc@textheight@#1\endcsname%
 \expandafter\newlength\csname puc@headsep@#1\endcsname%
%
 % adjust margins
 \expandafter\setlength{\csname puc@topmargin@#1\endcsname}{#2}%
 \expandafter\setlength{\csname puc@bottommargin@#1\endcsname}{#3}%
 \expandafter\setlength{\csname puc@leftmargin@#1\endcsname}{#4}%
 \expandafter\setlength{\csname puc@rightmargin@#1\endcsname}{#5}%
%
 % converts margins to text size
 \expandafter\setlength{\csname puc@textwidth@#1\endcsname}{\paperwidth}%
 \expandafter\addtolength{\csname puc@textwidth@#1\endcsname}{-\csname puc@leftmargin@#1\endcsname}%
 \expandafter\addtolength{\csname puc@textwidth@#1\endcsname}{-\csname puc@rightmargin@#1\endcsname}%
%
 \expandafter\setlength{\csname puc@oddsidemargin@#1\endcsname}{\csname puc@leftmargin@#1\endcsname}%
 \expandafter\addtolength{\csname puc@oddsidemargin@#1\endcsname}{-1in}%
 \expandafter\addtolength{\csname puc@oddsidemargin@#1\endcsname}{-\hoffset}%
%
 \expandafter\setlength{\csname puc@evensidemargin@#1\endcsname}{\csname puc@leftmargin@#1\endcsname}%
 \expandafter\addtolength{\csname puc@evensidemargin@#1\endcsname}{-1in}%
 \expandafter\addtolength{\csname puc@evensidemargin@#1\endcsname}{-\hoffset}%
%
 \expandafter\setlength{\csname puc@headsep@#1\endcsname}{\csname puc@topmargin@#1\endcsname}%
 \expandafter\addtolength{\csname puc@headsep@#1\endcsname}{-1in}%
 \expandafter\addtolength{\csname puc@headsep@#1\endcsname}{-\voffset}%
 \expandafter\addtolength{\csname puc@headsep@#1\endcsname}{-\topmargin}%
 \expandafter\addtolength{\csname puc@headsep@#1\endcsname}{-\headheight}%
%
 \expandafter\setlength{\csname puc@textheight@#1\endcsname}{\paperheight}%
 \expandafter\addtolength{\csname puc@textheight@#1\endcsname}{-\csname puc@topmargin@#1\endcsname}%
 \expandafter\addtolength{\csname puc@textheight@#1\endcsname}{-\csname puc@bottommargin@#1\endcsname}%
%
 % dynamic margin adjustment
 \expandafter\newcommand\csname puc@setmargins@#1\endcsname{%
   \setpage%
     {\csname puc@textheight@#1\endcsname}%
     {\csname puc@textwidth@#1\endcsname}%
     {\csname puc@evensidemargin@#1\endcsname}%
     {\csname puc@oddsidemargin@#1\endcsname}%
     {}{}{}%
     {\csname puc@headsep@#1\endcsname}%
     {}%
  }%
}


% Graduação: superior 2,5 cm, inferior 2,5 cm, esquerda 3,5 cm, direita 3,5 cm, em todas as páginas
\puc@setallmargins{text}{2.5cm}{2.5cm}{3.5cm}{3.5cm}



%%%
%%% To debug the layout
%%%

%\newcommand{\puc@leftmargin}[1]{\noindent\fbox{\begin{minipage}[top]{\textwidth}#1\end{minipage}}}
%\newcommand{\puc@rightmargin}[1]{\noindent\fbox{\begin{minipage}[top]{\textwidth}\begin{flushright}#1\end{flushright}\end{minipage}}}

\newcommand{\puc@leftmargin}[1]{\noindent\begin{minipage}[top]{\textwidth}#1\end{minipage}}
\newcommand{\puc@rightmargin}[1]{\puc@leftmargin{\begin{flushright}#1\end{flushright}}}


%%%
%%% line spacing
%%%

\onehalfspacing
\frenchspacing
\clubpenalty=2000
\emergencystretch=20pt
\pretolerance=500
\tolerance=2500
\widowpenalty=2000


%%%
%%% number of floats per page
%%%

\renewcommand{\floatpagefraction}{.7}
\renewcommand{\topfraction}{.7}
\renewcommand{\bottomfraction}{.7}
\renewcommand{\textfraction}{.3}
\setcounter{totalnumber}{10}
\setcounter{topnumber}{10}
\setcounter{bottomnumber}{10}


%%%
%%% subfigures
%%%

%\newcommand*\thesubfloatfigure{\alph{subfloatfigure}}
\renewcommand{\thesubfigure}{\alph{subfigure}}
%\newcommand{\@thesubfigure}{\thesubfigure:\space}
%\renewcommand{\p@subfigure}{}

%%%
%%% Fonts
%%%

%% \newcommand{\arial}{\fontfamily{arial}}
\renewcommand{\familydefault}{\sfdefault}
\newcommand{\arial}{\sf}

%%%
%%% Section titles
%%%

\titleformat{name=\chapter}			%% the command
   [display]					%% the shape
%%   {\singlespacing\large\fontfamily{arial}\bfseries\selectfont}
%%   %% the format (whole title)
   {\singlespacing\large\arial\bfseries}	%% the format (whole title)
   {\thechapter}				%% the label
   {0pt}					%% label title sep (space)
   {}					%% before (code)
   []						%% after (code)

% this alters "before" spacing (the second length argument) to 0
\titlespacing*{\chapter}	%% command
   {0pt}			%% left
   {-20pt}			%% before [pagestyle is not empty]
   {30pt}			%% after
   %% []			%% right

\titleformat{name=\section}
   [display]
   {\penalty -5000\singlespacing\normalsize\arial\bfseries}
   {\thesection}
   {0pt}
   {}
   {}

\titleformat{name=\section,numberless}
   [display]
   {\penalty -5000\singlespacing\normalsize\arial\bfseries}
   {}
   {0pt}
   {}
   {}

\titleformat{name=\subsection}
   [display]
   {\penalty -4000\singlespacing\normalsize\arial\bfseries}
   {\thesubsection}
   {0pt}
   {}
   {}

\titleformat{name=\subsection,numberless}
   [display]
   {\penalty -4000\singlespacing\normalsize\arial\bfseries}
   {}
   {0pt}
   {}
   {}

\titleformat{name=\subsubsection}
   [display]
   {\penalty -3000\singlespacing\normalsize\arial\bfseries}
   {\thesubsubsection}
   {0pt}
   {}
   {}

\titleformat{name=\subsubsection,numberless}
   [display]
   {\penalty -3000\singlespacing\normalsize\arial\bfseries}
   {\thesubsubsection}
   {0pt}
   {}
   {}

\titleformat{name=\paragraph}
   [runin]
   {\singlespacing\normalsize\arial\bfseries}
   {}
   {2\wordsep}
   {}
   {}

\titleformat{name=\subparagraph}
   [runin]
   {\singlespacing\normalsize\arial\bfseries}
   {}
   {2\wordsep}
   {}
   {}


%%%
%%% page styles
%%%

%%\makeatletter%
\newcommand{\puc@setpagestyle}{%
 \pagestyle{fancy}%
 \fancyhf{}% delete current setting for header and footer
 % Só o número da página, no alto à direita (inclusive na 1ª página de capítulo)
 \setlength{\headwidth}{\textwidth}% o cabeçalho acompanha a mancha de texto (3,5 cm de cada lado)
 \fancyhead[R]{\arial\thepage}%
 \fancypagestyle{plain}{\fancyhf{}\fancyhead[R]{\arial\thepage}\renewcommand{\headrulewidth}{0pt}}%
 \renewcommand{\headrulewidth}{0pt}%
}
\fancypagestyle{empty}{\fancyhead{} \fancyfoot{} \renewcommand{\headrulewidth}{0pt}}%
\fancypagestyle{plain}{\fancyhead{} \fancyfoot{} \renewcommand{\headrulewidth}{0pt}}%


%%%
%%% table of contents
%%%

\renewcommand*{\l@figure}[2]{%
  \ifnum \c@lofdepth >\z@
    \vskip \cftbeforefigskip
    {%\leftskip \cftfigindent\relax
     \rightskip\z@\rightskip \@tocrmarg
     \parfillskip -\rightskip
     %\parindent\z@\parindent \cftfigindent\relax
    \@afterindenttrue
     \interlinepenalty\@M
     \leavevmode
     \@tempdima \cftfignumwidth\relax
     \let\@cftbsnum \cftfigpresnum
     \let\@cftasnum \cftfigaftersnum
     \let\@cftasnumb \cftfigaftersnumb
     \null\nobreak%\advance\leftskip \@tempdima \null\nobreak\hskip -\leftskip
     \arial%
     {\cftfigfont #1}\nobreak
     \cftfigfillnum{#2}}%
   \fi
  }


\renewcommand*{\l@table}[2]{%
  \ifnum\c@lotdepth >\z@
    \vskip \cftbeforetabskip
    {%\leftskip \cfttabindent\relax
     \rightskip \@tocrmarg
     \parfillskip -\rightskip
     %\parindent \cfttabindent\relax
     \@afterindenttrue
     \interlinepenalty\@M
     \leavevmode
     \@tempdima \cfttabnumwidth\relax
     \let\@cftbsnum \cfttabpresnum
     \let\@cftasnum \cfttabaftersnum
     \let\@cftasnumb \cfttabaftersnumb
     %\advance\leftskip \@tempdima
     \null\nobreak%\hskip -\leftskip
     \arial%
     {\cfttabfont #1}\nobreak
     \cfttabfillnum{#2}}%
   \fi
  }

\renewcommand*{\l@algocf}[2]{%\leftskip \cfttabindent\relax
    \vskip \cftbeforefigskip
    {\leftskip \cftfigindent\relax
     \rightskip\z@\rightskip \@tocrmarg
     \parfillskip -\rightskip
     \parindent\z@\parindent \cftfigindent\relax
     \@afterindenttrue
     \interlinepenalty\@M
     \leavevmode
     \@tempdima \cftfignumwidth\relax
     \let\@cftbsnum \cftfigpresnum
     \let\@cftasnum \cftfigaftersnum
     \let\@cftasnumb \cftfigaftersnumb
     \null\nobreak\advance\leftskip \@tempdima \null\nobreak\hskip -\leftskip
     \arial%
     \hspace{-1.5em}{#1}\nobreak
     \cftfigfillnum{#2}}%
}

\renewcommand\l@lstlisting[2]{\@dottedtocline{1}{0pt}{\cfttabnumwidth}{\arial\lstlistingname~ #1}{#2}}

\setlength{\cfttabnumwidth}{3em}
\setlength{\cftfignumwidth}{3em}

\setcounter{tocdepth}{3}
\setcounter{lofdepth}{3}
\setcounter{lotdepth}{3}
\setcounter{secnumdepth}{3}

\renewcommand{\cfttoctitlefont}{\large \arial \bfseries}
\setlength{\cftbeforetoctitleskip}{-5pt}
\renewcommand{\cftloftitlefont}{\large \arial \bfseries}
\setlength{\cftbeforeloftitleskip}{-5pt}
\renewcommand{\cftlottitlefont}{\large \arial \bfseries}
\setlength{\cftbeforelottitleskip}{-5pt}
%% Remove dots of content line in talbe of contents, tables and figure
\renewcommand{\cftdot}{}
\renewcommand{\cftsecfont}{}
\setlength{\cftbeforesecskip}{\parskip}
\setlength{\cftbeforesubsecskip}{0pt}
\setlength{\cftchapnumwidth}{1.9em}
\setlength{\cftsecnumwidth}{2.5em}
\setlength{\cftsubsecnumwidth}{3.1em}
\setlength{\cftsubsubsecnumwidth}{3.7em}
\renewcommand{\cftchapindent}{0pt}
\renewcommand{\cftsecindent}{0pt}
\renewcommand{\cftsubsecindent}{0pt}
\renewcommand{\cftsubsubsecindent}{0pt}

%%%
%%% citations
%%%

%\def\@cite#1#2{[{#1\if@tempswa , #2\fi}]}
%\def\@citeb#1#2{({#1\if@tempswa , #2\fi})}


%%%
%%% theorems environments
%%%

\renewcommand{\theequation}{\thechapter-\arabic{equation}}
\newtheorem{definition}{Definição}[chapter]
\newtheorem{theorem}[definition]{Teorema}
\newtheorem{proposition}[definition]{Proposição}
\newtheorem{corollary}[definition]{Corolário}
\newenvironment{proof}{\par \noindent \textit{Prova}.}{\hfill $\blacksquare$}


%%%
%%% space in environment
%%%

\AfterBegin{itemize}{\addtolength{\itemsep}{-0.5em}}
\renewcommand{\labelitemi}{--}
\BeforeBegin{equation}{\vspace{-0.5em}}
\BeforeEnd{equation}{\vspace{-0.5em}}
\BeforeBegin{theorem}{\vspace{-0.4em}}
\BeforeEnd{theorem}{\vspace{-0.2em}}
\BeforeBegin{definition}{\vspace{-0.4em}}
\BeforeEnd{definition}{\vspace{-0.2em}}
\BeforeBegin{corollary}{\vspace{-0.4em}}
\BeforeEnd{corollary}{\vspace{-0.2em}}
\BeforeBegin{proposition}{\vspace{-0.4em}}
\BeforeEnd{proposition}{\vspace{-0.2em}}


%%%
%%% Front matter elements
%%%

%%\makeatletter

\newcommand{\puc@usecolour}{false}
\newcommand{\usecolour}[1]{\renewcommand{\puc@usecolour}{#1}}


\newcommand{\puc@author}{}
\renewcommand{\author}[1]{\renewcommand{\puc@author}{#1}}

\newcommand{\puc@authorR}{}
\newcommand{\authorR}[1]{\renewcommand{\puc@authorR}{#1}}

\newcommand{\puc@advisor}{}
\newcommand{\puc@advisorT}{}
\newcommand{\advisor}[2]{%
  \renewcommand{\puc@advisor}{#1}%
  \renewcommand{\puc@advisorT}{#2}}
\newcommand{\puc@advisorlabel}{}
\newcommand{\puc@advisorlabellc}{}

\newcommand{\puc@advisorR}{}
\newcommand{\advisorR}[1]{\renewcommand{\puc@advisorR}{#1}}

%% the advisor's institution and symbol if not the university itself
\newcommand{\puc@coadvisor}{}
\newcommand{\puc@coadvisorT}{}
\newcommand{\coadvisor}[2]{%
  \renewcommand{\puc@coadvisor}{#1}%
  \renewcommand{\puc@coadvisorT}{#2}}
\newcommand{\puc@coadvisorlabel}{}
\newcommand{\puc@coadvisorlabellc}{}

\newcommand{\puc@coadvisorR}{}
\newcommand{\coadvisorR}[1]{\renewcommand{\puc@coadvisorR}{#1}}

\newcommand{\puc@course}{Engenharia da Computação}
\newcommand{\curso}[1]{\renewcommand{\puc@course}{#1}}
\newcommand{\puc@degree}{Engenheiro de Computação}
\newcommand{\titulacao}[1]{\renewcommand{\puc@degree}{#1}}
\newcommand{\puc@discipline}{Projeto Final}
\newcommand{\puc@disciplineuk}{Undergraduate Thesis}
\newcommand{\disciplina}[2]{%
  \renewcommand{\puc@discipline}{#1}%
  \renewcommand{\puc@disciplineuk}{#2}}

\newcommand{\puc@title}{}
\renewcommand{\title}[1]{\renewcommand{\puc@title}{#1}}

\newcommand{\puc@titleuk}{}
\newcommand{\titleuk}[1]{\renewcommand{\puc@titleuk}{#1}}

\newcommand{\puc@subtitle}{}
\newcommand{\subtitle}[1]{\renewcommand{\puc@subtitle}{#1}}

%% \day, \month e \year viram comandos de configuração com um argumento. Os
%% originais (registradores do TeX) são guardados e restaurados antes do
%% \begin{document}, pois o babel os usa para calcular \today.
\let\puc@primday\day
\let\puc@primmonth\month
\let\puc@primyear\year
\AddToHook{begindocument/before}{%
  \let\day\puc@primday
  \let\month\puc@primmonth
  \let\year\puc@primyear
}

\newcommand{\puc@day}{}
\renewcommand{\day}[1]{\renewcommand{\puc@day}{#1}}

\newcommand{\puc@month}{}
\renewcommand{\month}[1]{\renewcommand{\puc@month}{#1}}

\newcommand{\puc@year}{}
\renewcommand{\year}[1]{\renewcommand{\puc@year}{#1}}

\newcommand{\puc@city}{Rio de Janeiro}
\newcommand{\city}[1]{\renewcommand{\puc@city}{#1}}

\newcommand{\puc@department}{}
\newcommand{\department}[1]{\renewcommand{\puc@department}{#1}}

\newcommand{\puc@program}{}
\newcommand{\program}[1]{\renewcommand{\puc@program}{#1}}

\newcommand{\puc@school}{}
\newcommand{\school}[1]{\renewcommand{\puc@school}{#1}}

\newcommand{\puc@university}{Pontifícia Universidade Católica do Rio de Janeiro}
\newcommand{\university}[1]{\renewcommand{\puc@university}{#1}}

\newcommand{\puc@uni}{PUC-Rio}
\newcommand{\uni}[1]{\renewcommand{\puc@uni}{#1}}

\newcommand{\puc@acknowledgment}{}
\newcommand{\acknowledgment}[1]{\renewcommand{\puc@acknowledgment}{#1}}

\newcommand{\key}[1]{}
\newcommand{\puc@keywords}{}
\newcommand{\keywords}[1]{\renewcommand{\puc@keywords}{#1}}

\newcommand{\puc@keywordsuk}{}
\newcommand{\keywordsuk}[1]{\renewcommand{\puc@keywordsuk}{#1}}

\newcommand{\puc@abstract}{}
\renewcommand{\abstract}[1]{\renewcommand{\puc@abstract}{#1}}%

\newcommand{\puc@abstractuk}{}
\newcommand{\abstractuk}[1]{\renewcommand{\puc@abstractuk}{#1}}%

\newcommand{\puc@tablesmode}{figtab}
\newcommand{\tablesmode}[1]{\renewcommand{\puc@tablesmode}{#1}}

\newcommand{\puc@algorithmsmode}{use}
\newcommand{\algorithmsmode}[1]{\renewcommand{\puc@algorithmsmode}{#1}}

\newcommand{\puc@codesmode}{use}
\newcommand{\codesmode}[1]{\renewcommand{\puc@codesmode}{#1}}

\newcommand{\puc@abreviationsmode}{use}
\newcommand{\abreviationsmode}[1]{\renewcommand{\puc@abreviationsmode}{#1}}

\newboolean{hasepigraph}
\setboolean{hasepigraph}{false}
\newif\if@pucepigraph\@pucepigraphfalse
\newcommand{\puc@epigraph}{}
\newcommand{\epigraph}[1]{%
  \renewcommand{\puc@epigraph}{#1}%
  \@pucepigraphtrue%
  \setboolean{hasepigraph}{true}%
}

\newcommand{\puc@epigraphauthor}{}
\newcommand{\epigraphauthor}[1]{\renewcommand{\puc@epigraphauthor}{#1}}

\newcommand{\puc@epigraphbook}{}
\newcommand{\epigraphbook}[1]{\renewcommand{\puc@epigraphbook}{#1}}

\newcommand{\puc@abreviationstitle}{Lista de Abreviaturas}
\newcommand{\abreviationstitle}[1]{\renewcommand{\puc@abreviationstitle}{#1}}%

\newcommand{\puc@abreviationstitleuk}{List of Abreviations}
\newcommand{\abreviationstitleuk}[1]{\renewcommand{\puc@abreviationstitleuk}{#1}}%


%%%
%%% translations
%%%

\newcommand{\autor}[1]{\author{#1}}
\newcommand{\autorR}[1]{\authorR{#1}}
\newcommand{\orientador}[2]{\advisor{#1}{#2}}
\newcommand{\orientadorR}[1]{\advisorR{#1}}
\newcommand{\coorientador}[1]{\coadvisor{#1}}
\newcommand{\coorientadorR}[1]{\coadvisorR{#1}}
\newcommand{\titulo}[1]{\title{#1}}
\newcommand{\titulouk}[1]{\titleuk{#1}}
\newcommand{\subtitulo}[1]{\subtitle{#1}}
\newcommand{\dia}[1]{\day{#1}}
\newcommand{\mes}[1]{\month{#1}}
\newcommand{\ano}[1]{\year{#1}}
\newcommand{\cidade}[1]{\city{#1}}
\newcommand{\departamento}[1]{\department{#1}}
\newcommand{\programa}[1]{\program{#1}}
\newcommand{\centro}[1]{\school{#1}}
\newcommand{\universidade}[1]{\university{#1}}
%\newcommand{\uni}[1]{\uni{#1}}
%\newcommand{\CDD}[1]{\CDD{#1}}
\newcommand{\agradecimentos}[1]{\acknowledgment{#1}}
\newcommand{\chave}[1]{\key{#1}}
\newcommand{\chaves}[1]{\keywords{#1}}
\newcommand{\chavesuk}[1]{\keywordsuk{#1}}
\newcommand{\resumo}[1]{\abstract{#1}}
\newcommand{\resumouk}[1]{\abstractuk{#1}}
\newcommand{\modotabelas}[1]{\tablesmode{#1}}
\newcommand{\modoabreviacoes}[1]{\abreviationsmode{#1}}
\newcommand{\modoalgoritmos}[1]{\algorithmsmode{#1}}
\newcommand{\modocodigos}[1]{\codesmode{#1}}
\newcommand{\epigrafe}[1]{\epigraph{#1}}
\newcommand{\epigrafeautor}[1]{\epigraphauthor{#1}}
\newcommand{\epigrafelivro}[1]{\epigraphbook{#1}}
\newcommand{\tituloglossario}[1]{\abreviationstitle{#1}}


%%%
%%% The title
%%%

\newcommand{\puc@thetitle}{%
  \if@brazilianlanguage
    \puc@title%
  \else
    \puc@titleuk%
  \fi
}%


%%%
%%% acknowledgment
%%%

\newcommand{\puc@showacknowledgment}{%
  \cleardoublepage%
  \puc@setmargins@text%
  \markboth{Agradecimentos}{Agradecimentos}%
  \thispagestyle{empty}%
  \onehalfspacing\rmfamily%
  \if@brazilianlanguage
    \noindent \large \arial \textbf{Agradecimentos}%
  \else
    \noindent \large \arial \textbf{Acknowledgments}%
  \fi
  \rmfamily \normalsize
  \vspace*{\stretch{1}} \par%
  \noindent
  \puc@acknowledgment%
  \vspace*{\stretch{1}} \par%
}

%%%
%%% tables
%%%
\newcommand{\puc@figuretext}{Figura}
\newcommand{\puc@figuretextuk}{Figure}

\newcommand{\puc@tabletext}{Tabela}
\newcommand{\puc@tabletextuk}{Table}

\newcommand{\puc@algorithmext}{Algoritmo}
\newcommand{\puc@algorithmextuk}{Algorithm}

\renewcommand{\cftfigfont}{%
  \if@brazilianlanguage
    \puc@figuretext~%
  \else
    \puc@figuretextuk~
  \fi}

\renewcommand{\cfttabfont}{%
  \if@brazilianlanguage
    \puc@tabletext~%
  \else
    \puc@tabletextuk~
  \fi}


%\renewcommand*{\thealgocf}{Algorithm~\arabic{algocf}}
\let\oldl@algocf\l@algocf
\if@brazilianlanguage
  \renewcommand{\l@algocf}[2]{\oldl@algocf{\puc@algorithmext~ #1}{#2}}%
\else
  \renewcommand{\l@algocf}[2]{\oldl@algocf{\puc@algorithmextuk~ #1}{#2}}%
\fi


\newcommand{\puc@showtables}{%
  \cleardoublepage%
  \puc@setmargins@text%
  \if@brazilianlanguage
    \renewcommand{\contentsname}{Sumário}%
    \renewcommand{\listfigurename}{Lista de figuras}%
    \renewcommand{\listtablename}{Lista de tabelas}%
    \renewcommand{\listalgorithmcfname}{Lista de algoritmos}%
    \renewcommand{\lstlistingname}{Código}%
    \renewcommand{\lstlistlistingname}{Lista de Códigos}%
  \else
    \renewcommand{\contentsname}{Table of contents}%
    \renewcommand{\listfigurename}{List of figures}%
    \renewcommand{\listtablename}{List of tables}%
    \renewcommand{\listalgorithmcfname}{List of algorithms}%
    \renewcommand{\lstlistingname}{Code}%
    \renewcommand{\lstlistlistingname}{List of codes}%
  \fi
  \markboth{\contentsname}{\contentsname}%
  \thispagestyle{empty}%
  \pdfbookmark[0]{\contentsname}{anchor:contents}%
  \singlespacing\rmfamily%
  \tableofcontents%
  \ifthenelse{\equal{\puc@tablesmode}{fig} \or \equal{\puc@tablesmode}{figtab}}%
  {%
    \clearpage%
    \markboth{\listfigurename}{\listfigurename}%
    \thispagestyle{empty}%
    \phantomsection
    \listoffigures%
    %\cftaddtitleline{toc}{section}{\listfigurename}{}%
  }{}%
  \ifthenelse{\equal{\puc@tablesmode}{tab} \or \equal{\puc@tablesmode}{figtab}}%
  {%
    \clearpage%
    \markboth{\listtablename}{\listtablename}%
    \phantomsection
    \thispagestyle{empty}%
    \listoftables%
    %\cftaddtitleline{toc}{section}{\listtablename}{}%
  }{}%
  \ifthenelse{\equal{\puc@algorithmsmode}{use}}%
  {%
    \clearpage%
    \markboth{\listalgorithmcfname}{\listalgorithmcfname}%
    \thispagestyle{empty}%
    \renewcommand\@dotsep{10000}
    \listofalgorithms%
    %\cftaddtitleline{toc}{section}{\listalgorithmcfname}{}%
  }{}%
  \ifthenelse{\equal{\puc@codesmode}{use}}%
  {%
    \clearpage%
    \markboth{\lstlistlistingname}{\lstlistlistingname}%
    \thispagestyle{empty}%
    \renewcommand\@dotsep{10000}
    \lstlistoflistings%
    %\cftaddtitleline{toc}{section}{\lstlistlistingname}{}%
  }{}%
  \ifthenelse{\equal{\puc@abreviationsmode}{use}}%
  {%
    \clearpage%
    \thispagestyle{empty}%
    \if@brazilianlanguage
      \chapter*{\puc@abreviationstitle}%
      \markboth{\puc@abreviationstitle}{\puc@abreviationstitle}%
      %\cftaddtitleline{toc}{section}{\puc@abreviationstitle}{}%
    \else
      \chapter*{\puc@abreviationstitleuk}%
      \markboth{\puc@abreviationstitleuk}{\puc@abreviationstitleuk}%
      %\cftaddtitleline{toc}{section}{\puc@abreviationstitleuk}{}%
    \fi
    \input{0-abrevs}%
  }{}%
}


%%%
%%% epigraph
%%%

\newcommand{\puc@showepigraph}{%
  \cleardoublepage%
  \puc@setmargins@text%
  \markboth{\contentsname}{\contentsname}%
  \thispagestyle{empty}%
  \singlespacing%
  \vspace*{\stretch{1}}\par\indent
  \hspace*{4.8cm}%
  \begin{minipage}[c]{8.2cm}%
  \begin{flushright}
  \it\rmfamily \puc@epigraph%
  \end{flushright}
  \end{minipage}%
  \hspace*{\stretch{1}}%
  \par%
  \begin{flushright}%
  \textbf{\rmfamily\puc@epigraphauthor}, \textit{\rmfamily\puc@epigraphbook}.%
  \end{flushright}%
  }


%%%
%%% index (to have the right bookmark in the pdf)
%%%

\renewenvironment{theindex}{%
  \if@twocolumn%
    \@restonecolfalse%
  \else%
    \@restonecoltrue%
  \fi%
  \twocolumn%
  \columnseprule \z@%
  \columnsep 35\p@%
  \chapter*{\indexname}%
  \addcontentsline{toc}{chapter}{\indexname}%
  \markboth{\indexname}{\indexname}
  \parskip\z@ \@plus .3\p@\relax%
  \let\item\@idxitem%
}{%
  \if@restonecol\onecolumn\else\clearpage\fi%
}


%%%
%%% Pré-texto do Projeto Final: capa, folha de rosto, resumo e abstract do manual do aluno
%%%

% Capa: universidade, título, subtítulo, autor, projeto, centro, departamento, curso, local e data.
% Todo o texto da capa e da folha de rosto fica alinhado à direita.
\newcommand{\puc@showcover}{%
  \ifthenelse{\equal{\puc@school}{}}{\renewcommand{\puc@school}{Centro Técnico Científico - CTC}}{}%
  \puc@setmargins@text%
  \thispagestyle{empty}%
  \singlespacing\arial%
  \begin{flushright}%
    {\centering\normalsize\bfseries \MakeUppercase{\puc@university}\par}%
    \vspace*{\stretch{0.5}}%
    {\Large\bfseries \puc@thetitle\relax\par}%
    \ifthenelse{\equal{\puc@subtitle}{}}{}{\vspace{0.5cm}{\large \puc@subtitle\par}}%
    \vspace*{\stretch{1}}%
    {\large\bfseries \puc@author\par}%
    \vspace*{\stretch{1}}%
    {\large\bfseries PROJETO FINAL DE GRADUAÇÃO\par}%
    \vspace*{\stretch{0.5}}%
    {\normalsize\bfseries \MakeUppercase{\puc@school}\par}%
    \vspace{0.5cm}%
    {\normalsize\bfseries DEPARTAMENTO DE \MakeUppercase{\puc@department}\par}%
    \vspace{0.5cm}%
    {\normalsize Curso de Graduação em \puc@course\par}%
    \vspace*{\stretch{1}}%
    {\normalsize \puc@city, \puc@month\ de \puc@year\par}%
  \end{flushright}%
  \clearpage%
}

% Folha de rosto: logo da PUC, autor, título, subtítulo, finalidade, orientador, local e data
\newcommand{\puc@showfront}{%
  \puc@setmargins@text%
  \thispagestyle{empty}%
  \pdfbookmark[0]{\puc@thetitle}{anchor:title}%
  \singlespacing\arial%
  \begin{flushright}%
    \includegraphics[height=2.2cm]{puc}\par%
    \vspace*{\stretch{1}}%
    {\large\bfseries \puc@author\par}%
    \vspace*{\stretch{2}}%
    {\Large\bfseries \puc@thetitle\relax\par}%
    \ifthenelse{\equal{\puc@subtitle}{}}{}{\vspace{0.5cm}{\large \puc@subtitle\par}}%
    \vspace*{\stretch{2}}%
    \hfill\begin{minipage}{0.55\textwidth}%
      \raggedright\normalsize%
      \setlength{\parindent}{0pt}%
      \hyphenpenalty=10000 \exhyphenpenalty=50 %
      Relatório de \puc@discipline, apresentado ao programa de Graduação do Departamento de
      \puc@department{} da \puc@uni{} como requisito parcial para a obtenção do título de
      \puc@degree.\par%
      \vspace{0.8cm}%
      \puc@advisorlabel: \ifthenelse{\equal{\puc@advisorT}{}}{}{\puc@advisorT\ }\puc@advisor\par%
      \ifthenelse{\equal{\puc@coadvisor}{}}{}{%
        \puc@coadvisorlabel: \ifthenelse{\equal{\puc@coadvisorT}{}}{}{\puc@coadvisorT\ }\puc@coadvisor\par}%
    \end{minipage}\par%
    \vspace*{\stretch{3}}%
    \puc@city \\ \puc@month\ de \puc@year%
  \end{flushright}%
  \clearpage%
}

% Resumo e palavras-chave (português). Sem \clearpage: Resumo e Abstract dividem a folha adicional.
\newcommand{\puc@showabstract}{%
  \if@americanlanguage \selectlanguage{brazilian}\fi%
  \markboth{Resumo}{Resumo}%
  \pdfbookmark[0]{Resumo}{anchor:abstract}%
  \noindent {\large\bfseries Resumo}\par%
  \vspace{0.5cm}%
  \noindent \puc@authorR. \puc@advisorR\ifthenelse{\equal{\puc@coadvisor}{}}{}{. \puc@coadvisorR}.
  \textbf{\puc@title\ifthenelse{\equal{\puc@subtitle}{}}{}{: \puc@subtitle}}. \puc@city, \puc@year.
  \pageref{LastPage} p. Relatório de \puc@discipline\ -- Departamento de \puc@department.
  \puc@university.\par%
  \vspace{0.5cm}%
  \noindent \puc@abstract\par%
  \vspace{0.5cm}%
  \noindent {\large\bfseries Palavras-chave}\par%
  \renewcommand{\key}[1]{##1; }%
  {\raggedright\noindent \StrGobbleRight{\puc@keywords}{3}.\par}%
  \if@americanlanguage \selectlanguage{american}\fi%
  \clearpage
}

% Abstract e keywords (inglês)
\newcommand{\puc@showabstractuk}{%
  \if@brazilianlanguage \selectlanguage{american}\fi%
  \markboth{Abstract}{Abstract}%
  \emergencystretch=10em%
  \noindent {\large\bfseries Abstract}\par%
  \vspace{0.5cm}%
  \noindent \puc@authorR. \puc@advisorR\ (Advisor)%
  \ifthenelse{\equal{\puc@coadvisor}{}}{}{. \puc@coadvisorR\ (Co-advisor)}.
  \textbf{\puc@titleuk}. \puc@city, \puc@year. \pageref{LastPage} p. \puc@disciplineuk\
  -- Departamento de \puc@department. \puc@university.\par%
  \vspace{0.5cm}%
  \noindent \puc@abstractuk\par%
  \vspace{0.5cm}%
  \noindent {\large\bfseries Keywords}\par%
  \renewcommand{\key}[1]{##1; }%
  {\raggedright\noindent \StrGobbleRight{\puc@keywordsuk}{3}.\par}%
  \if@brazilianlanguage \selectlanguage{brazilian}\fi%
  \clearpage
}

% Folha adicional: Resumo e Abstract na mesma página (cada um com cerca de 10 linhas)
\newcommand{\puc@showabstracts}{%
  \clearpage%
  \puc@setmargins@text%
  \thispagestyle{empty}%
  \singlespacing\arial%
  \puc@showabstract%
  \vspace{1.2cm}%
  \puc@showabstractuk%
  \clearpage%
}

% Ordem do manual: capa, folha de rosto, epígrafe (opcional), agradecimentos (opcional),
% resumo e abstract, sumário, listas de figuras e tabelas, conteúdo e referências.
% Não há folha de aprovação, ficha catalográfica nem dedicatória.
\newcommand{\puc@showfrontmatter}{%
  \pagestyle{empty}%
  \puc@showcover%
  \puc@showfront%
  \puc@showabstract%
  \puc@showabstractuk%
  \if@brazilianlanguage
    \selectlanguage{brazilian}%
  \else
    \selectlanguage{american}%
  \fi
  \puc@showtables%
  \clearpage%
  \puc@setmargins@text%
  \onehalfspacing%
  \rmfamily%
  \puc@setpagestyle%
}


\AtBeginDocument{%
  \renewcommand{\key}[1]{#1. }
  \if@brazilianlanguage
    \special{ pdf: docinfo << /Author (\puc@author) /Title (\puc@title)
      /Keywords (\puc@keywords) >> }%
  \else
    \special{ pdf: docinfo << /Author (\puc@author) /Title (\puc@titleuk) /Keywords (\puc@keywords) >> }%
  \fi
}

%% caps odities, we won't fight and define both the capitilzaed and
%% laower case version of the labels we need.

\AfterBegin{document}%
  {
   \if@brazilianlanguage
     \renewcommand{\puc@advisorlabel}{Orientador}%
     \renewcommand{\puc@advisorlabellc}{orientador}%
     \renewcommand{\puc@coadvisorlabel}{Co-orientador}%
     \renewcommand{\puc@coadvisorlabellc}{co-orientador}%
     \addto\captionsbrazilian{\renewcommand{\bibname}{Referências}}% NBR 6023: "Referências"
   \else
     \renewcommand{\puc@advisorlabel}{Advisor}%
     \renewcommand{\puc@advisorlabellc}{advisor}%
     \renewcommand{\puc@coadvisorlabel}{Co-advisor}%
     \renewcommand{\puc@coadvisorlabellc}{co-advisor}%
     \addto\captionsamerican{\renewcommand\bibname{Bibliography}}
   \fi
   \makeatletter\puc@showfrontmatter\makeatother%
   \renewcommand{\familydefault}{\rmdefault}
 }


%% Local Variables:
%% mode: LaTeX
%% End:
\endinput
%%
%% End of file `ThesisPUC.cls'.