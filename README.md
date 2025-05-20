Para utilizar o conversor é necessário ter o Microsoft Word instalado
# conversor_cojur
pip install  
fastapi  
uvicorn  
python-multipart  
pywin32  
chardet  
jinja2  
bs4

uvicorn main:app --host 0.0.0.0 --port 8000

Recursos do conversor  
Estilizado com CSS e JavaScript  
Possui arquivo de log do servidor  
Possui banco de dados sqlite3 para salvar quantidade de arquivos convertidos
Possui a rota /estatisticas para visualizar a quantidade de arquivos convertidos