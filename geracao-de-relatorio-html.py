# importa as bibliotecas
import pandas as pd, base64, os, io
from IPython.display import display, HTML
from PIL import Image

# define o diretório de imagens
image_dir = "C:/geracao-de-relatorio-html/imagens/"

# define o arquivo csv
csv_filepath = "C:/geracao-de-relatorio-html/base-de-dados.csv"

# define o arquivo html de destino
html_filepath = "C:/geracao-de-relatorio-html/relatorio.html"

# lista todos os arquivos de imagens dentro do diretório
image_files = os.listdir(image_dir)

# cria um dataframe vazio com as colunas para o código e a codificação da imagem
image_data = pd.DataFrame(columns=["codigo", "imagem"])

# percorre por cada arquivo de imagem
for image_file in image_files:
    # obtém o código dividindo o nome do arquivo pelo ponto e extraindo a primeira parte
    code = image_file.split(".")[0]
    # cria o caminho completo para o arquivo de imagem usando o diretório e o nome do arquivo
    image_path = os.path.join(image_dir, image_file)
    # abre a imagem usando o módulo PIL (Python Imaging Library)
    image = Image.open(image_path)
    # redimensiona a imagem para que a largura seja 150 pixels e a altura seja ajustada de acordo para manter a proporção original
    image_resized = image.resize((150, int(image.size[1] * 150 / image.size[0])))
    # cria um buffer de bytes para armazenar a imagem redimensionada
    image_bytes = io.BytesIO()
    # salva a imagem redimensionada no buffer usando o formato png
    image_resized.save(image_bytes, format = "PNG")
    # codifica os bytes da imagem em uma string base64 para armazenar no dataframe
    image_str = base64.b64encode(image_bytes.getvalue()).decode("utf-8")
    # adiciona um novo registro ao dataframe com o código e a imagem codificada
    image_data = pd.concat([image_data, pd.DataFrame({"codigo": [code], "imagem": [image_str]})], ignore_index = True)

# lê o arquivo csv com informações adicionais
csv_data = pd.read_csv(csv_filepath, dtype = "str", delimiter = ";")

# cruza os dados das imagens com os dados do arquivo csv usando a coluna de código como chave
merged_data = pd.merge(csv_data, image_data, on = "codigo")

# gera uma tabela html para exibir os dados
html = '<table>'
# define o estilo para as células de cabeçalho e células de dados
style = 'style="border: 1px solid black;"'
# define um estilo exclusivo para limitar a largura da célula de descrição
description_style = 'style="border: 1px solid black; max-width: 600px; overflow: hidden; padding: 5px;"'
# adiciona uma linha de cabeçalho com os nomes das colunas
html += '<tr><th {}>Código</th><th {}>Data de Cadastro</th><th {}>Descrição</th><th {}>Imagem</th></tr>'.format(style, style, style, style)
# percorre por cada linha do dataframe
for index, row in merged_data.iterrows():
    # cria uma tag html <img> para exibir a imagem no navegador
    image_tag = '<img src="data:image/png;base64,{}">'.format(row['imagem'])
    # adiciona uma nova linha à tabela com os dados da iteração atual
    html += '<tr><td {}>{}</td><td {}>{}</td><td {}>{}</td><td {}>{}</td></tr>'.format(style, row['codigo'], style, row["data_de_cadastro"], description_style, row["descricao"], style, image_tag)
# fecha a tabela adicionando a tag de fechamento
html += '</table>'

# salva o html em um arquivo
with open(html_filepath, "w") as f:
    f.write(html)
