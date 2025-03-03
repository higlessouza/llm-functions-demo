from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
import time
import base64
from src.services.open_ai_service import OpenAiService
from bs4 import BeautifulSoup

class Trf6ScrapingService:
    def __init__(self):
        self.open_ai_service = OpenAiService()
        self.options = Options()
        # Adicione capacidades desejadas diretamente às opções
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")

    def consultar_processo(self, numero_processo):
        # URL do WebDriver remoto
        remote_url = "https://standalone-chrome-production-0e32.up.railway.app/wd/hub"

        # Inicializar o driver remoto (sem o parâmetro desired_capabilities)
        self.driver = RemoteWebDriver(command_executor=remote_url, options=self.options)

        # URL do site de consulta
        url = "https://eproc1g.trf6.jus.br/eproc/externo_controlador.php?acao=processo_consulta_publica&hash=31552c89c24f8436cb56f4295ed0e7f7"
        self.driver.get(url)

        time.sleep(2)  # Espera o site carregar

        # Preencher o número do processo
        campo_processo = self.driver.find_element(By.XPATH, '//*[@id="txtNumProcesso"]')
        campo_processo.send_keys(numero_processo)

        # Implementação com retry para o captcha
        max_tentativas = 3
        tentativa_atual = 0
        captcha_valido = False

        while not captcha_valido and tentativa_atual < max_tentativas:
            tentativa_atual += 1
            print(f"Tentativa de captcha {tentativa_atual} de {max_tentativas}")

            # Capturar e salvar a imagem do CAPTCHA
            captcha_element = self.driver.find_element(By.XPATH, '//*[@id="lblInfraCaptcha"]/img')
            captcha_image = captcha_element.screenshot_as_png
            captcha_base64 = base64.b64encode(captcha_image).decode('utf-8')

            # Enviar a imagem para o OpenAI
            code_captcha = self.open_ai_service.get_image_context(captcha_base64)

            # Limpar o campo captcha se for uma tentativa subsequente
            if tentativa_atual > 1:
                input_captcha = self.driver.find_element(By.XPATH, '//*[@id="txtInfraCaptcha"]')
                input_captcha.clear()

            # Definir captcha
            input_captcha = self.driver.find_element(By.XPATH, '//*[@id="txtInfraCaptcha"]')
            input_captcha.send_keys(code_captcha)

            # Submeter o formulário
            campo_processo.send_keys(Keys.RETURN)

            # Aguardar carregamento da próxima página
            time.sleep(3)

            # Verificar se o captcha foi aceito - verificar se há mensagem de erro
            try:
                mensagem_erro = self.driver.find_element(By.XPATH, '//div[@id="divInfraAviso"]')
                if "captcha" in mensagem_erro.text.lower() or "código de segurança" in mensagem_erro.text.lower():
                    print(f"Captcha incorreto: {mensagem_erro.text}")
                    # Clicar no botão OK para fechar a mensagem de erro
                    botao_ok = self.driver.find_element(By.XPATH, '//button[contains(text(), "OK")]')
                    botao_ok.click()
                    time.sleep(1)
                    continue
                else:
                    # Se há um erro, mas não relacionado ao captcha
                    print(f"Erro diferente do captcha: {mensagem_erro.text}")
                    raise Exception(f"Erro ao consultar processo: {mensagem_erro.text}")
            except Exception as e:
                if "no such element" in str(e).lower():
                    # Se não encontrou mensagem de erro, provavelmente o captcha foi aceito
                    print("Captcha aceito!")
                    captcha_valido = True
                else:
                    # Se foi outro tipo de erro
                    print(f"Erro ao verificar captcha: {str(e)}")
                    raise e

        if not captcha_valido:
            raise Exception(f"Falha ao resolver captcha após {max_tentativas} tentativas")

        # Capturar atualizações do processo
        atualizacoes = self.driver.find_elements(By.XPATH, '//*[@id="divInfraAreaProcesso"]/table')
        atualizacoes_html = [atualizacao.get_attribute('outerHTML') for atualizacao in atualizacoes]
        json_return = self.atualizacoes_html_to_json(atualizacoes_html)

        # Partes do processo
        partes = self.driver.find_elements(By.XPATH, '//*[@id="fldPartes"]/table')
        partes_html = [parte.get_attribute('outerHTML') for parte in partes]
        partes_json = self.partes_html_to_json(partes_html)

        self.driver.quit()
        return {"atualizacoes": json_return, "partes": partes_json}

    def atualizacoes_html_to_json(self, html_list):
        all_dados = []
        for html in html_list:
            soup = BeautifulSoup(html, 'html.parser')
            tabela = soup.find('table', {'class': 'infraTable'})
            if tabela:
                linhas = tabela.find_all('tr')[1:]
                for linha in linhas:
                    colunas = linha.find_all('td')
                    if len(colunas) == 5:
                        all_dados.append({
                            'Evento': colunas[0].text.strip(),
                            'Data/Hora': colunas[1].text.strip(),
                            'Descrição': colunas[2].text.strip(),
                            'Usuário': colunas[3].text.strip(),
                            'Documentos': colunas[4].text.strip()
                        })
        return all_dados

    def partes_html_to_json(self, html_list):
        all_dados = []
        for html in html_list:
            soup = BeautifulSoup(html, 'html.parser')
            tabela = soup.find('table', {'class': 'infraTable'})
            linhas = tabela.find_all('tr')[1:]
            for linha in linhas:
                colunas = linha.find_all('td')
                if len(colunas) == 2:
                    autor = colunas[0].get_text(separator="\n", strip=True).replace("  ", " ")
                    reu = colunas[1].get_text(separator="\n", strip=True).replace("  ", " ")
                    all_dados.append({
                        "Autor": autor,
                        "Réu": reu
                    })
        return all_dados