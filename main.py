from socket import timeout
from tokenize import cookie_re
import discord
from discord.ext import commands
from discord_components import *
import requests
import pymongo
import time
import os


default_intents = discord.Intents.default()
default_intents.members = True

bot = commands.Bot(command_prefix="!", intents=default_intents)

mongo_url = f"mongodb+srv://LighTender:" + open("MDP_DB.txt","r").readline().replace("\n", "") + "@cluster.do1ss.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
print(mongo_url)
cluster = pymongo.MongoClient(mongo_url)
db = cluster["database"]
collection_users = db["users"]
collection_games = db["games"]

ID_ROLE_MEMBRE = 973294837233233970


def check_if_it_is_me(ctx):
	return ctx.message.author.id == 338768773865537536

@bot.event
async def on_ready():
	DiscordComponents(bot)
	print("Le bot est pret")


@bot.command(name='renitialise_stat', help="Pour le gérant du serveur")
@commands.check(check_if_it_is_me)
async def reinitialise_stat(ctx):
    await ctx.message.delete()

    result = collection_users.find({})

    for x in result:
        joueur_id = x["_id"]

        collection_users.update_one(
            {"_id": joueur_id}, {"$set": {"pts": 0}})
        collection_users.update_one(
            {"_id": joueur_id}, {"$set": {"top1": 0}})
        collection_users.update_one(
            {"_id": joueur_id}, {"$set": {"parties": 0}})


@commands.cooldown(1, 60, commands.BucketType.user)
@bot.command(name='coc', help="", aliases=["url", "game"])
async def command_int(ctx,url:str):

    await ctx.message.delete(delay=60*5)
    if not 'https://www.codingame.com/clashofcode/clash/' in url:
        await ctx.send("L'URL n'est pas valide")
        return

    if url.find('/'):
        hexa = url.split('/')[-1]
        print(hexa)
        id_hexa = int(hexa[:8], 16)
        print(id_hexa)
        id_game = collection_games.find_one({"id": id_hexa})
        n = 0
        if id_game != None:
            await ctx.send("Ce jeu est déjà enregistré", timeout=10)
            return

        collection_games.insert_one({"_id": id_hexa, "hexa": hexa, "finish":0})

        return await ctx.send("Le jeu a été enregistré", timeout=5)
    else:
        return await ctx.send("URL invalide", timeout=10)


@commands.cooldown(1, 60, commands.BucketType.guild)
@bot.command(name='act', help="", aliases=["actalise", "actualise","actualisation"])
async def actualiser(ctx):

    await ctx.message.delete()

    all_game = collection_games.find({"finish":0})

    url = "https://www.codingame.com/services/ClashOfCode/findClashReportInfoByHandle"

    nb_game_actualiser = 0

    for game in all_game:
        r = requests.post(url, json=[game["hexa"]], timeout=2.50)
        replay = r.json()
        # print(replay)
        if replay["finished"]:
            nb_game_actualiser += 1
            # print("Game " + str(replay["publicHandle"]) + " is finished")
            # Ajouter les top 1 si le joueur existe et qu'il n'a pas 0%

            nb_joureur = len(replay["players"])

            for joueur in replay["players"]:
                if joueur["score"] != 0:
                    player_id = 0
                    # print("-------------------------------")
                    # print(joueur["codingamerNickname"])
                    for j in ctx.message.author.guild.members:
                        print(j.display_name)
                        if joueur["codingamerNickname"] == j.display_name:
                            player_id = j.id
                    if player_id != 0:
                        if joueur["rank"] == 1:
                            # print("Player " + str(joueur["codingamerNickname"]) + " is top 1")
                            collection_users.update_one(
                                {"_id": player_id}, {"$inc": {"top1": 1}})
                        # print("Player " + str(joueur["codingamerNickname"]) + " is in " + str(joueur["rank"]) + " rank")
                        collection_users.update_one(
                                {"_id": player_id}, {"$inc": {"pts": nb_joureur-joueur["rank"] + 1}})
                collection_users.update_one({"_id": player_id}, {"$inc": {"parties": 1}})
            collection_games.update_one(
            	{"_id": int(replay["publicHandle"][:8], 16)}, {"$inc": {"finish": 1}})
        time.sleep(1)
    if (nb_game_actualiser == 0):
        return await ctx.send("Aucune game n'a été actualisée", timeout=10)
    elif (nb_game_actualiser == 1):
        return await ctx.send("1 game a été actualisée", timeout=10)
    else:
        await ctx.send(f"{nb_game_actualiser} games ont été actualisées")


@commands.cooldown(1, 60, commands.BucketType.user)
@bot.command(name='hi', help="bienvenue", aliases=["hello"])
async def command_int(ctx):

    await ctx.message.delete()

    verif = False
    for role in ctx.message.author.roles:
        if role.id == ID_ROLE_MEMBRE:
            verif = True
    if verif:
        return await ctx.channel.send(f"Vous avez déjà le rôle @member, {ctx.author.mention}")

    member_id = ctx.author.id
    name = ctx.author.display_name

    role = discord.utils.find(
        lambda r: r.id == ID_ROLE_MEMBRE, ctx.author.guild.roles)

    await ctx.author.add_roles(role)

    collection_users.insert_one({"_id": member_id, "name": name, "top1":0, "pts":0, "parties":0})

    return await ctx.channel.send(f"Profil initialisé, Bienvenue !!, {ctx.author.mention}")


@bot.command(name='me', aliases=["moi","profile"])
async def rank(ctx):

    await ctx.message.delete()

    verif = False
    for role in ctx.message.author.roles:
        if role.id == ID_ROLE_MEMBRE:
            verif = True
    if not verif:
        return await ctx.channel.send(f"Vous n'êtes pas encore @member, faites `!hi` pour vous enregistrer, {ctx.author.mention}")

    member = ctx.message.author
    author_id = member.id
    result = collection_users.find({"_id": author_id})

    for x in result:
        joureur_parties = x["parties"]
        joureur_pts = x["pts"]
        joureur_top1 = x["top1"]

    embed = discord.Embed(
        title=f"**__{ctx.author.display_name}__**")

    embed.add_field(name="**Quelques chiffres:**",
                    value=f"Nombre de parties jouées: {joureur_parties}\nNombre de top 1: {joureur_top1}\nNombre de points : {joureur_pts}", inline=False)
    embed.set_thumbnail(url=ctx.author.avatar_url)

    await ctx.send(f"{ctx.author.mention}", embed=embed)

@bot.command(name='rank', aliases=["leaderboard", "classement", "pts"])
async def rank(ctx):

    await ctx.message.delete()

    result = collection_users.find({}).sort(
        [("pts", pymongo.DESCENDING), ("top1", pymongo.DESCENDING)])

    rank = []
    page = 1
    nb = 0

    for x in result:
        nb += 1
        joueur_name = x["name"]
        joueur_top1 = x["top1"]
        joueur_pts = x["pts"]
        rank.append((nb, joueur_name, joueur_top1, joueur_pts))

    message = ""
    max_page = page*10
    if max_page > rank[-1][0]-1:
        max_page = rank[-1][0]

    for i in range((page-1)*10, max_page):
        message += f"**{rank[i][0]}**. {rank[i][1]} : **{rank[i][3]}** pts, **{rank[i][2]}** top1\n"

    embed = discord.Embed(title="Classement", description=message)
    embed.set_footer(text=f"page {page}/{int(len(rank)/10)+1}")
    max_page_nb = int(len(rank)/10)+1

    if page == 1 and page == max_page_nb:
        m = await ctx.channel.send(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page", disabled=True), Button(style=1, label="Next Page", disabled=True)]])
    elif page == 1:
        m = await ctx.channel.send(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page", disabled=True), Button(style=1, label="Next Page")]])
    elif page == max_page_nb:
        m = await ctx.channel.send(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page"), Button(style=1, label="Next Page", disabled=True)]])
    else:
        m = await ctx.channel.send(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page"), Button(style=1, label="Next Page")]])

    while True:
        def check(res):
            return res.channel == ctx.channel
        res = await bot.wait_for("button_click", check=check)
        action = res.component.label
        if action == "Next Page":
            page += 1
        if action == "Previous Page":
            page -= 1

        message = ""
        max_page = page*10
        if max_page > rank[-1][0]-1:
            max_page = rank[-1][0]

        for i in range((page-1)*10, max_page):
            message += f"**{rank[i][0]}**. {rank[i][1]} : **{rank[i][3]}** pts, **{rank[i][2]}** top1\n"

        embed = discord.Embed(title="Classement", description=message)

        embed.set_footer(text=f"page {page}/{int(len(rank)/10)+1}")
        if page == 1 and page == max_page_nb:
            await m.edit(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page", disabled=True), Button(style=1, label="Next Page", disabled=True)]])
        elif page == 1:
            await m.edit(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page", disabled=True), Button(style=1, label="Next Page")]])
        elif page == max_page_nb:
            await m.edit(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page"), Button(style=1, label="Next Page", disabled=True)]])
        else:
            await m.edit(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page"), Button(style=1, label="Next Page")]])


@bot.command(name='top1', aliases=["top"])
async def rank(ctx):

    await ctx.message.delete()

    result = collection_users.find({}).sort(
        [("top1", pymongo.DESCENDING), ("pts", pymongo.DESCENDING)])

    rank = []
    page = 1
    nb = 0

    for x in result:
        nb += 1
        joueur_name = x["name"]
        joueur_top1 = x["top1"]
        joueur_pts = x["pts"]
        rank.append((nb, joueur_name, joueur_top1, joueur_pts))

    message = ""

    max_page = page*10
    if max_page > rank[-1][0]-1:
        max_page = rank[-1][0]

    for i in range((page-1)*10, max_page):
        message += f"**{rank[i][0]}**. {rank[i][1]} : **{rank[i][2]}** top1, **{rank[i][3]}** pts\n"

    embed = discord.Embed(title="Classement", description=message)
    embed.set_footer(text=f"page {page}/{int(len(rank)/10)+1}")
    max_page_nb = int(len(rank)/10)+1

    if page == 1 and page == max_page_nb:
        m = await ctx.channel.send(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page", disabled=True), Button(style=1, label="Next Page", disabled=True)]])
    elif page == 1:
        m = await ctx.channel.send(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page", disabled=True), Button(style=1, label="Next Page")]])
    elif page == max_page_nb:
        m = await ctx.channel.send(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page"), Button(style=1, label="Next Page", disabled=True)]])
    else:
        m = await ctx.channel.send(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page"), Button(style=1, label="Next Page")]])

    while True:
        def check(res):
            return res.channel == ctx.channel
        res = await bot.wait_for("button_click", check=check)
        action = res.component.label
        if action == "Next Page":
            page += 1
        if action == "Previous Page":
            page -= 1

        message = ""
        max_page = page*10
        if max_page > rank[-1][0]-1:
            max_page = rank[-1][0]

        for i in range((page-1)*10, max_page):
            message += f"**{rank[i][0]}**. {rank[i][1]} : **{rank[i][2]}** top1, **{rank[i][3]}** pts\n"

        embed = discord.Embed(title="Classement", description=message)

        embed.set_footer(text=f"page {page}/{int(len(rank)/10)+1}")
        if page == 1 and page == max_page_nb:
            await m.edit(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page", disabled=True), Button(style=1, label="Next Page", disabled=True)]])
        elif page == 1:
            await m.edit(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page", disabled=True), Button(style=1, label="Next Page")]])
        elif page == max_page_nb:
            await m.edit(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page"), Button(style=1, label="Next Page", disabled=True)]])
        else:
            await m.edit(f"{ctx.author.mention}", embed=embed, components=[[Button(style=1, label="Previous Page"), Button(style=1, label="Next Page")]])
"""
@bot.command(name='ping', help="pong")
async def command_int(ctx):
    await ctx.message.delete()
    await ctx.send("pong")
"""

bot.run(open("TOKEN.txt","r").readline())

