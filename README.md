# PLAYGROUND
Este repositório é designado para reter meus mini-projetos.

### Geração de relatório HTML
Este mini-projeto se trata da automação de um trabalho muito oneroso de se fazer manualmente.

Há uma base com várias imagens que devem ser cruzadas com os dados de uma planilha com informações adicionais.

Cada imagem é identificada por um código no nome do arquivo, por exemplo: "12345.png". Este código é a chave utizada para cruzar as imagens com os dados da planilha usando a coluna "codigo".

Inicialmente, todos os nomes dos arquivos desta base de imagens são listados em uma variável. Em seguida, para cada item da lista, uma linha com o código extraído do nome da imagem e a codificação da imagem é inserida dentro de um dataframe.

Após toda a lista ter sido iterada, os dados da planilha com as informações adicionais de cada objeto são lidos e carregados em outro dataframe. Então, o dataframe de imagens é cruzado com o dataframe de informações adicionais através da chave "codigo" presente em ambos. O resultado do cruzamento entre os dados é armazenado em um novo dataframe.

No final do processamento, a partir deste novo dataframe, um arquivo HTML é gerado compondo as informações de cada registro da planilha junto com a imagem correspondente gerando um relatório completo com todos os dados que se cruzaram.
