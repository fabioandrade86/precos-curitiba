# 🛒 Preços do Mercado · Curitiba

Página para celular e computador que mostra **onde a sua lista de compras sai mais barata** perto de casa, com os preços pesquisados pela Prefeitura de Curitiba no programa **Clique Economia** (SMSAN): cerca de 750 itens em 57 supermercados, de segunda a sexta.

**Página:** https://fabioandrade86.github.io/precos-curitiba/
- Perto da Barreirinha: https://fabioandrade86.github.io/precos-curitiba/?perto=barreirinha
- Perto do Alto da XV: https://fabioandrade86.github.io/precos-curitiba/?perto=altodaxv

## O que a página faz
- **Meu endereço:** digite onde mora (ou use a localização do celular) e escolha a distância (2, 5 ou 10 km). Tudo se recalcula para os mercados perto dali. O endereço fica salvo só no aparelho; para achar o ponto, ele é enviado ao geocodificador do OpenStreetMap.
- **Onde comprar:** total da sua lista em cada mercado perto de casa (ou uma cesta básica de exemplo).
- **Produtos:** busca, mais barato perto de você, mais barato na cidade, preço comum, gráfico desde 2023.
- **Subiu ou caiu:** 1 semana, 1 mês, 3 meses, 1 ano e desde o marco zero (06/11/2026, a última pesquisa antes de 08/11/2026).
- **Resumo da semana** pronto para mandar no WhatsApp, alerta de **menor preço em 12 meses**, planilha CSV e impressão/PDF.
- A lista fica salva no próprio celular (não vai para nenhum servidor).

## Como se atualiza
O workflow [`atualizar.yml`](.github/workflows/atualizar.yml) roda sozinho de segunda a sábado (01:40, 10:10 e 17:10 de Curitiba):
1. `scripts/geocode_lojas.py` localiza no mapa as lojas novas (só as que ainda não estão no cache).
1. `scripts/baixar.py` baixa os arquivos diários novos do espelho do Portal de Dados Abertos na UFPR (`dadosabertos.c3sl.ufpr.br/curitiba/CliqueEconomia`).
2. `scripts/build_data.py` valida o arquivo (colunas, códigos de produto, preços). **Se algo vier estranho, a publicação é cancelada** e a página continua com os dados anteriores. O GitHub manda e-mail avisando da falha.
3. Os arquivos novos são guardados em `dados/diarios/` e a página é publicada no GitHub Pages.

Para atualizar na hora: aba **Actions → Atualizar preços → Run workflow**.
O botão **Atualizar** da página busca a versão publicada mais recente.

## Arquivos
- `site/` — a página (HTML único + Chart.js local). `site/data/` é gerado pelo workflow.
- `dados/historico/` — histórico compacto 2023→09/2026 (origem: base pública do Clique Economia compilada em [nltncsr/clique-economia-prefeitura-curitiba-insights](https://github.com/nltncsr/clique-economia-prefeitura-curitiba-insights)).
- `dados/diarios/` — um arquivo por dia de pesquisa, no formato original da Prefeitura.
- `dados/lojas.json` — posição aproximada das lojas (usada quando o mapa não acha o número), bairros e **lojas extras** que a Prefeitura não pesquisa (ex.: Festval Hugo Lange/Itupava), com preço estimado pela média das outras lojas da mesma rede.
- `dados/geocache.json` — posição exata das lojas pelo endereço (OpenStreetMap), preenchida pelo workflow.

## Cuidados
- Os preços são os da prateleira no dia da pesquisa. Promoções podem já ter acabado: **confira na loja**.
- Preço de clube/fidelidade e de atacado não entram. Atacarejos (Assaí, Atacadão…) podem exigir compra em quantidade.
- Só há pesquisa de segunda a sexta; não dá para comparar com o fim de semana.
- Distâncias são em linha reta e aproximadas.

Dados: Prefeitura Municipal de Curitiba — SMSAN / Clique Economia, Portal de Dados Abertos.
