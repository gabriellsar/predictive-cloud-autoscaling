# Configuração do latexmk para o relatório (rode a partir de lib/report).
# Todos os arquivos gerados (aux, log, synctex, PDF) vão para aux/, que não
# vai para o Git. O PDF final é copiado para main.pdf ao fim de um build sem erros.
use Cwd qw(getcwd);
my $root = getcwd();

$pdf_mode = 1;
$pdflatex = 'pdflatex -synctex=1 -interaction=nonstopmode -file-line-error %O %S';
$out_dir  = 'aux';
$ENV{TEXINPUTS} = join(':', map { "$root/$_//" } qw(template chapters figures)) . ':';
$ENV{BIBINPUTS} = "$root/bibliography//:";
$ENV{BSTINPUTS} = "$root/template//:";

$success_cmd = 'cp aux/%R.pdf %R.pdf';
