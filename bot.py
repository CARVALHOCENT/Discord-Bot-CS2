import discord
import a2s
import json
import asyncio
import time
from discord import app_commands
from discord.ui import View, Button, Select
import os
from dotenv import load_dotenv
import aiohttp # Para a API da Faceit
from datetime import datetime # Para a API da Faceit

# --- CONFIGURAÇÃO ---
load_dotenv() # Carrega as variáveis do ficheiro .env
TOKEN = os.getenv("DISCORD_TOKEN") # Lê o token seguro
SERVERS_FILE = "servers.json"

# --- Configuração da API Faceit (DEFINIÇÃO GLOBAL) ---
FACEIT_API_KEY = os.getenv("FACEIT_API_KEY")
FACEIT_HEADERS = {
    'Authorization': f'Bearer {FACEIT_API_KEY}',
    'accept': 'application/json'
}
# --- Fim da Configuração Faceit ---

# --- NOVO: Configuração de Som ---
# Coloca o nome do teu ficheiro de som aqui. Tem de estar na mesma pasta do bot.
SOUND_FILE_ADORO_TE = "adorote.mp3" 
# -------------------------------

# --- CLIENT ---
intents = discord.Intents.default()
intents.voice_states = True # <-- NOVO: Permissão para ver estados de voz
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# --- Setup Hook para criar a sessão ---
@client.event
async def setup_hook():
    """Cria uma sessão aiohttp persistente quando o bot arranca."""
    client.http_session = aiohttp.ClientSession()
    print("Sessão aiohttp criada.")
# --- Fim do Setup Hook ---


# ===================================================================
# --- SECÇÃO: SERVIDORES CS2 (/mimiajuda) ---
# (Este código não foi alterado)
# ===================================================================

# --- FUNÇÃO: Ler lista de servidores ---
def get_server_list():
    try:
        with open(SERVERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ ERRO: Arquivo {SERVERS_FILE} não encontrado.")
        return []
    except json.JSONDecodeError:
        print(f"⚠️ ERRO: Arquivo {SERVERS_FILE} mal formatado.")
        return []

# --- FUNÇÃO: Consultar um único servidor ---
async def fetch_server_info(server):
    address = (server["ip"], server["porta"])
    try:
        start = time.perf_counter()
        info = await asyncio.wait_for(a2s.ainfo(address), timeout=2.5)
        ping = (time.perf_counter() - start) * 1000
        
        return {
            "status": "online", "name": info.server_name, "players": info.player_count,
            "max_players": info.max_players, "map": info.map_name, "ping": ping,
            "connect": f"```connect {server['ip']}:{server['porta']}```"
        }
    except Exception:
        return {
            "status": "offline", "name": server["nome"],
            "connect": f"`{server['ip']}:{server['porta']}`"
        }

# --- FUNÇÃO: Consultar e Ordenar Servidores ---
async def get_sorted_server_data(tipo=None, owner=None):
    server_list = get_server_list()
    
    filtered_list = server_list
    if owner and owner.lower() != "todos":
        owner_lower = owner.lower()
        filtered_list = [s for s in filtered_list if owner_lower in s["nome"].lower()]

    if tipo and tipo.lower() != "todos":
        tipo_lower = tipo.lower()
        filtered_list = [s for s in filtered_list if s["tipo"].lower() == tipo_lower]

    tasks = [fetch_server_info(server) for server in filtered_list]
    results = await asyncio.gather(*tasks)
    
    online_servers = []
    offline_servers = []
    
    for res in results:
        if res['status'] == 'online':
            if res['players'] < res['max_players']:
                online_servers.append(res)
        else:
            offline_servers.append(res)
            
    online_servers.sort(key=lambda s: s['ping'])
    return online_servers, offline_servers

# --- VIEW: Painel de Paginação ---
class PaginatedServerView(View):
    def __init__(self, online_servers, offline_servers, tipo, items_per_page=5):
        super().__init__(timeout=300)
        self.online_servers = online_servers
        self.offline_servers = offline_servers
        self.tipo = tipo.capitalize()
        self.items_per_page = items_per_page
        self.current_page = 1
        
        self.total_pages = (len(self.online_servers) + self.items_per_page - 1) // self.items_per_page
        if self.total_pages == 0:
            self.total_pages = 1
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        prev_button = Button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary, custom_id="prev", disabled=(self.current_page == 1))
        next_button = Button(label="Seguinte ➡️", style=discord.ButtonStyle.secondary, custom_id="next", disabled=(self.current_page == self.total_pages))
        prev_button.callback = self.prev_page
        next_button.callback = self.next_page
        self.add_item(prev_button)
        self.add_item(next_button)

    def create_page_embed(self):
        THUMBNAIL_LIST = [
            "https://i.imgur.com/oMdD9ED.png", # Imagem 1
            "https://i.imgur.com/HCGhP02.png", # Imagem 2
            "https://i.imgur.com/1wud9oj.png", # Imagem 3
            "https://i.imgur.com/lCtcvNn.png", # Imagem 4
            "https://i.imgur.com/3NCicBf.png"  # Imagem 5
        ]
        EMOJI_PLAYERS = "🧍"
        EMOJI_MAP = "🗺️"
        EMOJI_CONNECT = "🔗"
        EMOJI_ONLINE_TITLE = "✅"
        PING_LOW_EMOJI = "🟢"
        PING_MED_EMOJI = "🟡"
        PING_HIGH_EMOJI = "🔴"

        start_index = (self.current_page - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        servers_on_page = self.online_servers[start_index:end_index]
        
        embed = discord.Embed(
            title=f"🖥️ Status: {self.tipo} (Pág. {self.current_page}/{self.total_pages})",
            color=discord.Color.blurple(),
            description="Servidores ordenados pelo **melhor ping** (mais baixo)."
        )
        
        if not self.online_servers:
            embed.add_field(name="ℹ️ Nenhum servidor disponível", value=f"Nenhum servidor do tipo `{self.tipo}` (com vagas) foi encontrado.", inline=False)
        else:
            online_list_str = []
            for s in servers_on_page:
                if s['ping'] < 60: ping_emoji = PING_LOW_EMOJI
                elif s['ping'] < 100: ping_emoji = PING_MED_EMOJI
                else: ping_emoji = PING_HIGH_EMOJI
                
                online_list_str.append(
                    f"**{s['name']}**\n"
                    f"{EMOJI_PLAYERS} `{s['players']}/{s['max_players']}` | {ping_emoji} `{s['ping']:.1f} ms` | {EMOJI_MAP} `{s['map']}`\n"
                    f"{EMOJI_CONNECT} {s['connect']}"
                )
            embed.add_field(name=f"{EMOJI_ONLINE_TITLE} Online (Página {self.current_page}/{self.total_pages})", value="\n\n".join(online_list_str), inline=False)
        
        embed.set_footer(text=f"Total de {len(self.online_servers)} servidores online (com vagas) encontrados.")
        
        if THUMBNAIL_LIST: 
            try:
                image_index = (self.current_page - 1) % len(THUMBNAIL_LIST)
                THUMBNAIL_URL = THUMBNAIL_LIST[image_index]
                if THUMBNAIL_URL.startswith("https://"):
                    embed.set_thumbnail(url=THUMBNAIL_URL)
            except Exception as e:
                print(f"Erro ao definir thumbnail dinâmica: {e}") 
        
        return embed

    async def prev_page(self, interaction: discord.Interaction):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_page_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_page_embed()
            await interaction.response.edit_message(embed=embed, view=self)

# --- VIEWS: Filtros de Servidor ---
class OwnerSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Todos", description="Mostrar todos os donos", emoji="🌍"),
            discord.SelectOption(label="TUGA ARMY", description="Filtrar por TUGA ARMY", emoji="🛡️"),
            discord.SelectOption(label="SweetRicers", description="Filtrar por SweetRicers", emoji="🍬"),
            discord.SelectOption(label="CyberShoke", description="Filtrar por CyberShoke", emoji="⚡"),
        ]
        super().__init__(placeholder="1. Escolha o dono do servidor...", options=options, custom_id="owner_select")
    
    async def callback(self, interaction: discord.Interaction):
        self.view.selected_owner = self.values[0]
        await interaction.response.defer() 

class TypeSelect(Select):
    def __init__(self):
        EMOJI_TODOS = "🌍"
        EMOJI_PADRAO = "⚫"
        EMOJI_MAP = {"Retakes": "💣", "Surf": "🔪", "Jailbreak": "🔫", "FFA": "💥", "Arenas": "⚔️", "AWP": "🎯","Bhop": "🦘","Duelos":"🤺"}
        
        server_list = get_server_list()
        tipos = sorted(set(s["tipo"] for s in server_list if "tipo" in s))
        
        options = [discord.SelectOption(label="Todos", description="Mostrar todos os tipos", emoji=EMOJI_TODOS)]
        for t in tipos:
            emoji = EMOJI_MAP.get(t, EMOJI_PADRAO)
            options.append(discord.SelectOption(label=t, description=f"Filtrar por {t}", emoji=emoji))
        
        super().__init__(placeholder="2. Escolha o tipo de jogo...", options=options, custom_id="type_select")

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_type = self.values[0]
        await interaction.response.defer() 

class FilterView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.selected_owner = "Todos"
        self.selected_type = "Todos"
        self.add_item(OwnerSelect())
        self.add_item(TypeSelect())

    @discord.ui.button(label="🔍 Buscar Servidores", style=discord.ButtonStyle.success, custom_id="search_button", row=2)
    async def search_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content=f"🔍 A consultar servidores... (Dono: `{self.selected_owner}`, Tipo: `{self.selected_type}`)\nIsto pode demorar alguns segundos.",
            embed=None, view=None
        )
        
        online_servers, offline_servers = await get_sorted_server_data(tipo=self.selected_type, owner=self.selected_owner)
        view = PaginatedServerView(online_servers, offline_servers, self.selected_type)
        embed = view.create_page_embed()
        
        await interaction.edit_original_response(content=None, embed=embed, view=view)

# --- COMANDO: /mimiajuda ---
@tree.command(name="mimiajuda", description="Mostra o status dos servidores CS2 por categoria.")
async def mimiajuda(interaction: discord.Interaction):
    view = FilterView() 
    await interaction.response.send_message(
        "👋 Bem-vindo! Por favor, use os menus abaixo para filtrar os servidores e clique em 'Buscar'.", 
        view=view, ephemeral=True
    )

# ===================================================================
# --- FIM DA SECÇÃO: SERVIDORES CS2 ---
# ===================================================================


# ===================================================================
# --- SECÇÃO FACEIT (MODIFICADA PARA MENSAGENS PÚBLICAS) ---
# ===================================================================

async def get_faceit_player(nickname):
    """Busca os dados básicos de um jogador (ID, elo, nível, avatar)."""
    url = f"https://open.faceit.com/data/v4/players?nickname={nickname}"
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with client.http_session.get(url, headers=FACEIT_HEADERS, timeout=timeout) as resp:
            if resp.status == 200:
                print("DEBUG: [1/3] get_faceit_player SUCESSO")
                return await resp.json()
            else:
                print(f"DEBUG: [1/3] get_faceit_player FALHOU (Status: {resp.status})")
                return None
    except asyncio.TimeoutError:
        print("DEBUG: [1/3] get_faceit_player TIMEOUT")
        return "TIMEOUT"
    except Exception as e:
        print(f"Erro ao buscar jogador Faceit: {e}")
        return None

async def get_faceit_stats(player_id):
    """Busca as estatísticas gerais (K/D, Winrate) de um jogador."""
    url = f"https://open.faceit.com/data/v4/players/{player_id}/stats/cs2"
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with client.http_session.get(url, headers=FACEIT_HEADERS, timeout=timeout) as resp:
            if resp.status == 200:
                print("DEBUG: [2/3] get_faceit_stats SUCESSO")
                return await resp.json()
            else:
                print(f"DEBUG: [2/3] get_faceit_stats FALHOU (Status: {resp.status})")
                return None
    except asyncio.TimeoutError:
        print("DEBUG: [2/3] get_faceit_stats TIMEOUT")
        return "TIMEOUT"
    except Exception as e:
        print(f"Erro ao buscar stats Faceit: {e}")
        return None
        
async def get_faceit_history_24h(player_id):
    """Busca o histórico de partidas das últimas 24 horas."""
    from_timestamp = int(time.time()) - 86400 # 24 * 60 * 60
    url = f"https://open.faceit.com/data/v4/players/{player_id}/history?game=cs2&from={from_timestamp}&limit=100"
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with client.http_session.get(url, headers=FACEIT_HEADERS, timeout=timeout) as resp:
            if resp.status == 200:
                print("DEBUG: [3/3] get_faceit_history SUCESSO")
                return await resp.json()
            else:
                print(f"DEBUG: [3/3] get_faceit_history FALHOU (Status: {resp.status})")
                return None
    except asyncio.TimeoutError:
        print("DEBUG: [3/3] get_faceit_history TIMEOUT")
        return "TIMEOUT"
    except Exception as e:
        print(f"Erro ao buscar histórico Faceit: {e}")
        return None

# --- NOVA FUNÇÃO HELPER ---
async def get_last_match(player_id):
    """Busca a última partida (limit=1) de um jogador."""
    url = f"https://open.faceit.com/data/v4/players/{player_id}/history?game=cs2&limit=1"
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with client.http_session.get(url, headers=FACEIT_HEADERS, timeout=timeout) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get('items'):
                    print(f"DEBUG: [Veademo 1/3] get_last_match SUCESSO para {player_id}")
                    return data['items'][0] # Retorna o objeto da primeira partida
                else:
                    return None # Jogador sem histórico
            print(f"DEBUG: [Veademo 1/3] get_last_match FALHOU (Status: {resp.status})")
            return None
    except asyncio.TimeoutError:
        print(f"DEBUG: [Veademo 1/3] get_last_match TIMEOUT para {player_id}")
        return "TIMEOUT"
    except Exception as e:
        print(f"Erro ao buscar last match: {e}")
        return None

# --- NOVA FUNÇÃO HELPER ---
async def get_match_stats(match_id):
    """Busca as estatísticas detalhadas de uma partida específica."""
    url = f"https://open.faceit.com/data/v4/matches/{match_id}/stats"
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with client.http_session.get(url, headers=FACEIT_HEADERS, timeout=timeout) as resp:
            if resp.status == 200:
                print(f"DEBUG: [Veademo 3/3] get_match_stats SUCESSO para {match_id}")
                return await resp.json()
            print(f"DEBUG: [Veademo 3/3] get_match_stats FALHOU (Status: {resp.status})")
            return None
    except asyncio.TimeoutError:
        print(f"DEBUG: [Veademo 3/3] get_match_stats TIMEOUT para {match_id}")
        return "TIMEOUT"
    except Exception as e:
        print(f"Erro ao buscar match stats: {e}")
        return None
    
# --- FUNÇÃO DE LÓGICA (partilhada) ---
async def check_faceit_stats(interaction: discord.Interaction, nickname: str):
    """Função de lógica reutilizável que busca e envia o embed da Faceit."""
    
    print(f"\n--- Iniciando busca Faceit para: {nickname} ---")
    
    # 0. Verifica se a API Key da Faceit está configurada
    if not FACEIT_API_KEY:
        print("❌ ERRO: A FACEIT_API_KEY não está definida no ficheiro .env")
        await interaction.followup.send("❌ O bot não está configurado para aceder à API da Faceit.", ephemeral=True) 
        return

    # 1. Buscar dados básicos do jogador
    player_data = await get_faceit_player(nickname)
    
    if player_data == "TIMEOUT":
        await interaction.followup.send("❌ A API da Faceit demorou muito tempo a responder (Timeout). Tenta novamente.")
        return
    if not player_data:
        await interaction.followup.send(f"❌ Jogador '{nickname}' não encontrado. Verifica o nickname.")
        return

    player_id = player_data.get('player_id')
    avatar = player_data.get('avatar', '')
    profile_url = player_data.get('faceit_url', 'https://faceit.com').replace("{lang}", "en")
    
    # 2. Buscar estatísticas gerais
    stats_data = await get_faceit_stats(player_id)
    if stats_data == "TIMEOUT":
        await interaction.followup.send("❌ A API da Faceit demorou muito tempo a responder (Timeout). Tenta novamente.")
        return
    if not stats_data:
        await interaction.followup.send("❌ Este jogador não tem estatísticas de CS2 (ou perfil privado).")
        return

    # Extrair stats principais
    cs2_game_data = player_data.get('games', {}).get('cs2', {})
    elo = cs2_game_data.get('faceit_elo', 'N/A')
    level = cs2_game_data.get('skill_level', 'N/A')
    
    lifetime_stats = stats_data.get('lifetime', {})
    kd = lifetime_stats.get('Average K/D Ratio', 'N/A')
    hs_percent = lifetime_stats.get('Average Headshots %', 'N/A')
    win_rate = lifetime_stats.get('Win Rate %', 'N/A')
    matches = lifetime_stats.get('Matches', 'N/A')

    # 3. Calcular W/L das últimas 24h
    wins_24h = 0
    losses_24h = 0
    history_data = await get_faceit_history_24h(player_id)
    
    if history_data and history_data != "TIMEOUT":
        matches_list = history_data.get('items', [])
        
        print(f"DEBUG: Encontradas {len(matches_list)} partidas no histórico de 24h.")
        
        for match in matches_list:
            
            match_status = match.get('status', '').upper()
            if match_status != 'FINISHED':
                print(f"DEBUG: Ignorando partida {match.get('match_id')} (Status: {match_status})")
                continue 
            
            # --- INÍCIO DA CORREÇÃO LÓGICA ---
            my_faction_name = None # O que queremos encontrar (ex: "faction1")
            
            teams_dict = match.get('teams') 

            if not isinstance(teams_dict, dict):
                print(f"DEBUG: 'teams' não é um dicionário na partida {match.get('match_id')}, a ignorar.")
                continue 

            # Loop correto: iterar pelo NOME da fação (key) e DADOS da equipa (value)
            for faction_name, team_data in teams_dict.items():
                if my_faction_name: # Se já encontrámos, paramos
                    break
                
                if not isinstance(team_data, dict):
                    print(f"DEBUG: 'team_data' dentro de 'teams' não é um dict, a ignorar. Valor: {team_data}")
                    continue

                for p in team_data.get('players', []):
                    player_id_to_check = None
                    
                    if isinstance(p, dict):
                        player_id_to_check = p.get('player_id')
                    elif isinstance(p, str):
                        player_id_to_check = p
                    
                    if player_id_to_check == player_id:
                        # ENCONTRADO! Guarda o NOME DA FAÇÃO (a "key")
                        my_faction_name = faction_name 
                        print(f"DEBUG: Jogador encontrado na {faction_name}")
                        break 
            # --- FIM DA CORREÇÃO LÓGICA ---
            
            # Compara o NOME da fação vencedora
            winner_faction_name = match.get('results', {}).get('winner')
            
            if my_faction_name and winner_faction_name:
                print(f"DEBUG: A minha fação: {my_faction_name} | Fação vencedora: {winner_faction_name}")
                if my_faction_name == winner_faction_name:
                    wins_24h += 1
                else:
                    losses_24h += 1
            else:
                 if not my_faction_name:
                        print(f"DEBUG: Não foi possível encontrar a equipa do jogador {nickname} na partida {match.get('match_id')}")
                 if not winner_faction_name:
                        print(f"DEBUG: Partida {match.get('match_id')} não tem 'winner' nos resultados.")
    else:
        print("DEBUG: W/L de 24h não foi calculado (histórico falhou ou deu timeout).")


    # 4. Criar o Embed
    wl_str = f"{wins_24h}V / {losses_24h}D"
    
    embed_color = discord.Color.orange()
    if wins_24h > losses_24h:
        embed_color = discord.Color.green()
    elif losses_24h > wins_24h:
        embed_color = discord.Color.red()

    embed = discord.Embed(
        title=f"Estatísticas Faceit de {player_data.get('nickname')}",
        color=embed_color,
        url=profile_url
    )
    
    if avatar:
        embed.set_thumbnail(url=avatar)
    
    embed.add_field(name="Elo", value=f"**{elo}**", inline=True)
    embed.add_field(name="Nível", value=f"**{level}**", inline=True)
    embed.add_field(name="Partidas Totais", value=f"{matches}", inline=True)
    embed.add_field(name="K/D (Geral)", value=f"{kd}", inline=True)
    embed.add_field(name="Win Rate (Geral)", value=f"{win_rate}%", inline=True)
    embed.add_field(name="HS (Geral)", value=f"{hs_percent}%", inline=True)
    
    embed.add_field(name="Resultado (Últimas 24h)", value=f"**{wl_str}**", inline=False)
    embed.set_footer(text=f"ID: {player_id} • Atualizado às {datetime.now().strftime('%H:%M:%S')}")
    embed.set_author(name="Faceit Stats", icon_url="https://files.catbox.moe/6v01M.png")

    await interaction.followup.send(embed=embed)
    print(f"--- Busca Faceit para {nickname} CONCLUÍDA ---")

# --- Comando /checkmyelo ---
@tree.command(name="checkmyelo", description="Verifica as estatísticas de um jogador da Faceit.")
@app_commands.describe(nickname="O nick do jogador na Faceit")
async def checkmyelo(interaction: discord.Interaction, nickname: str):
    # --- ALTERAÇÃO: 'ephemeral=True' removido do defer ---
    await interaction.response.defer()
    await check_faceit_stats(interaction, nickname)

# --- Comando /elodorei ---
@tree.command(name="elodorei", description="Verifica as estatísticas do BICHOREI (Bichoblamef).")
async def elodorei(interaction: discord.Interaction):
    # --- ALTERAÇÃO: 'ephemeral=True' removido do defer ---
    await interaction.response.defer()
    hardcoded_nickname = "Bichoblamef"
    await check_faceit_stats(interaction, hardcoded_nickname)

# --- NOVO COMANDO /veademo ---
@tree.command(name="veademo", description="Mostra as stats da última partida de um jogador.")
@app_commands.describe(nickname="O nick do jogador na Faceit")
async def veademo(interaction: discord.Interaction, nickname: str):
    await interaction.response.defer() # Resposta pública
    print(f"\n--- Iniciando busca /veademo para: {nickname} ---")

    # 1. Obter ID do Jogador
    player_data = await get_faceit_player(nickname)
    if player_data == "TIMEOUT":
        await interaction.followup.send("❌ A API da Faceit demorou muito (Timeout). Tenta novamente.")
        return
    if not player_data:
        await interaction.followup.send(f"❌ Jogador '{nickname}' não encontrado.")
        return
    
    player_id = player_data.get('player_id')
    avatar = player_data.get('avatar', '')

    # 2. Obter Última Partida
    last_match = await get_last_match(player_id)
    if last_match == "TIMEOUT":
        await interaction.followup.send("❌ A API da Faceit demorou muito (Timeout). Tenta novamente.")
        return
    if not last_match:
        await interaction.followup.send(f"❌ '{nickname}' não tem histórico de partidas CS2.")
        return

    match_id = last_match.get('match_id')
    # O link da partida está no objeto do histórico
    match_url = last_match.get('faceit_url', 'https://faceit.com').replace("{lang}", "en")

    # 3. Obter Stats da Partida
    stats_data = await get_match_stats(match_id)
    if stats_data == "TIMEOUT":
        await interaction.followup.send("❌ A API da Faceit demorou muito (Timeout). Tenta novamente.")
        return
    if not stats_data or 'rounds' not in stats_data or not stats_data['rounds']:
        await interaction.followup.send(f"❌ Não foi possível obter estatísticas para a partida: {match_id}")
        return

    # 4. Analisar os Dados da Partida
    try:
        round_data = stats_data['rounds'][0]
        map_name = round_data['round_stats'].get('Map', 'N/A')
        score = round_data['round_stats'].get('Score', 'N/A')

        player_stats_obj = None
        team_won = False

        for team in round_data.get('teams', []):
            if player_stats_obj: break # Se já encontrámos, paramos
            for player in team.get('players', []):
                if player.get('player_id') == player_id:
                    player_stats_obj = player.get('player_stats', {})
                    team_won = team.get('team_stats', {}).get('Team Win') == "1"
                    break
        
        if not player_stats_obj:
            await interaction.followup.send(f"❌ Não foi possível encontrar as stats do jogador '{nickname}' nessa partida.")
            return

        # 5. Extrair Stats Finais
        kills = player_stats_obj.get('Kills', 'N/A')
        deaths = player_stats_obj.get('Deaths', 'N/A')
        assists = player_stats_obj.get('Assists', 'N/A')
        kd_ratio = player_stats_obj.get('K/D Ratio', 'N/A')
        hs_percent = player_stats_obj.get('Headshots %', 'N/A')
        mvps = player_stats_obj.get('MVPs', 'N/A')

        embed_color = discord.Color.green() if team_won else discord.Color.red()
        result_text = "🏆 Vitória" if team_won else "💔 Derrota"

        # 6. Construir o Embed
        embed = discord.Embed(
            title=f"Última Partida de {nickname}",
            color=embed_color,
            url=match_url
        )
        if avatar:
            embed.set_thumbnail(url=avatar)
        
        embed.set_author(name=f"{result_text} em {map_name} ({score})", icon_url="https://files.catbox.moe/6v01M.png") # Icone Faceit
        embed.add_field(name="Kills", value=f"**{kills}**", inline=True)
        embed.add_field(name="Deaths", value=f"**{deaths}**", inline=True)
        embed.add_field(name="Assists", value=f"**{assists}**", inline=True)
        embed.add_field(name="K/D", value=f"**{kd_ratio}**", inline=True)
        embed.add_field(name="Headshots", value=f"{hs_percent}%", inline=True)
        embed.add_field(name="MVPs", value=f"{mvps}", inline=True)
        
        embed.add_field(name="🔗 Link da Partida", value=f"[Ver demo na Faceit]({match_url})", inline=False)
        embed.set_footer(text=f"Match ID: {match_id}")

        await interaction.followup.send(embed=embed)
        print(f"--- Busca /veademo para {nickname} CONCLUÍDA ---")
    
    except Exception as e:
        print(f"ERRO CRÍTICO ao analisar stats da partida {match_id}: {e}")
        await interaction.followup.send("❌ Ocorreu um erro ao ler os dados desta partida. A API pode ter retornado um formato inesperado.")

# ===================================================================
# --- FIM DA SECÇÃO FACEIT ---
# ===================================================================

# ===================================================================
# --- NOVO: SECÇÃO DE VOZ (Toca 2x e Sai) ---
# ===================================================================

@tree.command(name="adoro-te", description="O bot entra na tua call para te dizer algo especial (2x).")
async def adoro_te(interaction: discord.Interaction):
    # 1. Verifica se o utilizador está numa call
    if interaction.user.voice is None:
        await interaction.response.send_message("❌ Tens de estar numa call para eu entrar!", ephemeral=True)
        return

    # 2. Verifica se o ficheiro de som existe
    if not os.path.exists(SOUND_FILE_ADORO_TE):
        print(f"❌ ERRO: Ficheiro de som '{SOUND_FILE_ADORO_TE}' não foi encontrado.")
        await interaction.response.send_message("❌ Desculpa, não consigo encontrar o meu ficheiro de som.", ephemeral=True)
        return
        
    # 3. Entra na call do utilizador
    channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client 

    try:
        if voice_client is not None:
            # Se já está na call, move-se
            await voice_client.move_to(channel)
        else:
            # Se não está, liga-se
            voice_client = await channel.connect()
    except Exception as e:
        print(f"Erro ao ligar ou mover: {e}")
        await interaction.response.send_message("❌ Não consigo ligar-me a esse canal de voz.", ephemeral=True)
        return

    # 4. Lógica para tocar 2x e sair
    
    # Variável para contar quantas vezes tocou
    play_count = 0

    def after_play_callback(error):
        """Esta função é chamada automaticamente quando um som termina."""
        nonlocal play_count # Diz à função para usar a variável 'play_count' de fora
        play_count += 1
        
        if error:
            print(f"Erro ao tocar o som: {error}")
            # Se deu erro, não faz mais nada
            return

        if play_count == 1:
            # Se tocou 1 vez, toca a segunda vez
            print("DEBUG: Som tocou 1 vez. A tocar a 2ª vez.")
            source_again = discord.FFmpegPCMAudio(SOUND_FILE_ADORO_TE)
            voice_client.play(source_again, after=after_play_callback)
        
        elif play_count == 2:
            # Se tocou 2 vezes, desconecta-se
            print("DEBUG: Som tocou 2 vezes. A desconectar.")
            # Como estamos num 'callback' (sync), não podemos usar 'await'.
            # Usamos 'run_coroutine_threadsafe' para pedir ao bot para se desconectar.
            asyncio.run_coroutine_threadsafe(voice_client.disconnect(), client.loop)

    # Inicia a *primeira* vez
    print("DEBUG: A tocar a 1ª vez.")
    source_first = discord.FFmpegPCMAudio(SOUND_FILE_ADORO_TE)
    voice_client.play(source_first, after=after_play_callback)

    await interaction.response.send_message("💖 A tocar... (2x)", ephemeral=True) # Resposta simples


@tree.command(name="para", description="Faz o bot parar de tocar e sair da call.")
async def para(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    
    # Verifica se o bot está numa call
    if voice_client is None:
        await interaction.response.send_message("❌ Eu não estou em nenhuma call.", ephemeral=True)
        return
        
    # Para de tocar e desconecta-se
    await voice_client.disconnect()
    await interaction.response.send_message("👋 Até à próxima!", ephemeral=True)

# ===================================================================
# --- FIM DA SECÇÃO DE VOZ ---
# ===================================================================

# --- EVENTO: Bot pronto (CORRIGIDO) ---
@client.event
async def on_ready():
    await tree.sync() 
    
    print(f"✅ Bot logado como {client.user}")
    print("📡 Comandos sincronizados globalmente.")
    print("💬 Usa /mimiajuda, /checkmyelo, /elodorei, /veademo, /adoro-te, ou /para.") # --- ESTA É A LINHA CORRETA ---


# --- EXECUÇÃO (Com verificação de Token) ---
if TOKEN is None:
    print("="*40)
    print("❌ ERRO: DISCORD_TOKEN NÃO ENCONTRADO")
    print("Verifica se criaste o ficheiro .env e definiste a variável DISCORD_TOKEN.")
    print("="*40)
elif FACEIT_API_KEY is None:
    print("="*40)
    print("⚠️ AVISO: FACEIT_API_KEY NÃO ENCONTRADA")
    print("O comando /mimiajuda vai funcionar, mas os comandos de Faceit irão falhar.")
    print("Adiciona a FACEIT_API_KEY ao teu ficheiro .env.")
    print("="*40)
    client.run(TOKEN) # Mesmo assim, liga o bot
else:
    client.run(TOKEN)