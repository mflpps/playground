# PLAYGROUND
Este repositório é designado para reter meus mini-projetos.

### Geração de relatório HTML
Este mini-projeto se trata de uma automação de um trabalho muito oneroso de se fazer manualmente.

Há uma base com várias imagens no diretório /geracao-de-relatorio-html/imagens/ que devem ser cruzadas com os dados de uma planilha com informações adicionais que encontra-se em /geracao-de-relatorio-html/base-de-dados.csv.

Cada imagem é identificada por um código no nome do arquivo, por exemplo: "12345.png". Este código é a chave utizada para cruzar as imagens com os dados da planilha usando a coluna "codigo".

No final do processamento, com os dados já cruzados, um arquivo HTML é gerado em /geracao-de-relatorio-html/geracao-de-relatorio-html.html compondo as informações de cada registro da planilha junto com a imagem correspondente.
