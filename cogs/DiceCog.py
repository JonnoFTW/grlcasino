import discord
import jsonrpc_requests
from discord.ext import commands
from random import randint, choice
from datetime import datetime
import asyncio
from .BaseCog import BaseCog


class DiceCog(BaseCog):
    dice = {
        '1': '⚀',
        '2': '⚁',
        '3': '⚂',
        '4': '⚃',
        '5': '⚄',
        '6': '⚅',
    }
    min_buy_in = 0.01
    max_buy_in = 10
    channel_id = 405191547357757442

    def __init__(self, bot):
        self.bot = bot
        self.grlc = bot.grlc
        self.conn = bot.conn

    @staticmethod
    def _roll_string():
        return "{}{}".format(randint(1, 6), randint(1, 6))
        
    @staticmethod
    def str2score(score):
        return sum([int(x) for x in score])


    @commands.command(aliases=['roll'])
    async def start(self, ctx, *, amount: float):
        """
        Start a dicegame for a specified amount: $start 0.75
        :param message:
        :return:
        """
        if ctx.message.channel.id != self.channel_id:
            return
        # check if the user already has a game in progress
        current_game = self.get_current_game(ctx.author.id)
        if current_game is not None:
            await ctx.send(f'{ctx.author.mention}: Someone must accept your previous game before you can start another')
            return
        if amount <= self.min_buy_in or amount > self.max_buy_in:
            await ctx.send(f"{ctx.author.mention}: Games must be between {self.min_buy_in} and {self.max_buy_in} GRLC")
            return
        fee = amount * self.bot.bot_fee

        if await self.check_balance(amount, ctx):
            self.grlc.move_between_accounts(ctx.author.id, self.bot.bot_id, fee + amount)

            c = self.conn.cursor()
            rollA = self._roll_string()
            rollB = self._roll_string()
            while self.str2score(rollA) == self.str2score(rollB):
                rollB = self._roll_string()

            c.execute("INSERT INTO dice VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (ctx.author.id,
                       None,
                       amount,
                       None,
                       datetime.now(),
                       rollA, rollB)
                      )
            self.conn.commit()
            msg = f"{ctx.author.mention} has started a game worth {amount}. Someone else must accept with '$accept {ctx.author.mention}' to complete the game"
            print(msg)
            await ctx.send(msg)

    @commands.command()
    async def current(self, ctx):
        """
        List current games
        :param ctx:
        :return:
        """
        if ctx.message.channel.id != self.channel_id:
            return
        c = self.conn.cursor()
        msg = "Current games are:\n"
        rows = 0
        for row in c.execute("SELECT * FROM main.dice WHERE winnerUserId IS NULL"):
            user = self.bot.get_user(row['userIdA'])
            msg += f"{user.mention} {row['value']}\n"
            rows += 1
        if rows == 0:
            await ctx.send(f"{ctx.author.mention} There are no games at the moment. Start one using $start 0.5")
        else:
            await ctx.send(msg)

    @commands.command()
    async def accept(self, ctx, *, user: discord.User):
        """
        Accept a game from another player: $accept @peace#1234
        :param ctx:
        :param user:
        :return:
        """
        if ctx.message.channel.id != self.channel_id:
            return
        # get the game row for the other user where there is no winner
        if user.id == ctx.author.id:
            await ctx.send(f'{ctx.author.mention}: You can\'t accept your own game')
            return
        row = self.get_current_game(user.id)

        if row is None:
            await ctx.send(f'{ctx.author.mention}: {user.mention} has no games currently')
            return
        # if the user is not signed up, they can't play
        # print(row.keys())
        fee = row['value'] * self.bot.bot_fee
        if await self.check_balance(row['value'], ctx):
            # Play the game!!!!
            # put the playerB in there

            def str2emoji(score):
                return "{}{}".format(self.dice[score[0]], self.dice[score[1]])

            a_score = self.str2score(row['rollA'])
            b_score = self.str2score(row['rollB'])
            a_user = ctx.bot.get_user(row['userIdA'])
            msg = "{} rolled: {}, {} rolled: {}, ".format(
                a_user.mention,
                str2emoji(row['rollA']),
                ctx.author.mention,
                str2emoji(row['rollB'])
            )
            if a_score > b_score:
                winner = a_user
                loser = ctx.author
            else:
                winner = ctx.author
                loser = a_user

            c = self.conn.cursor()
            c.execute("UPDATE main.dice SET userIdB = ?, winnerUserId = ? WHERE userIdA = ? AND winnerUserId is NULL",
                      (ctx.author.id, winner.id, user.id))
            self.conn.commit()
            # bot takes a 0.8% fee from both users before,
            # then the game amount is moved from the loser to winner

            self.grlc.move_between_accounts(ctx.author.id, self.bot.bot_id, fee + row['value'])
            self.grlc.move_between_accounts(self.bot.bot_id, winner.id, row['value'] * 2)
            bread = choice(['bread', 'french_bread', 'stuffed_flatbread', 'grlc'])
            msg += "{} wins {} GRLC! :{}:".format(winner.mention, row['value'], bread)
            await ctx.send(msg)

    @commands.command()
    async def canceldice(self, ctx):
        """
        Cancel your current game
        :param ctx:
        :return:
        """
        game = self.get_current_game(ctx.author.id)
        if game is None:
            await ctx.send(f"{ctx.author.id} you have no game to cancel")
            return
        c = self.conn.cursor()
        c.execute("DELETE FROM main.dice WHERE rowid = ?", (game['rowid'],))
        self.conn.commit()
        fee = game['value'] * self.bot.bot_fee
        self.grlc.move_between_accounts(self.bot.bot_id, ctx.author.id, fee + game['value'])
        await ctx.send(f"{ctx.author.mention} cancelled and refunded game worth {game['value']} + {fee}")

    def get_current_game(self, id):
        c = self.conn.cursor()
        c.execute("SELECT rowid, * FROM main.dice WHERE userIdA = ? AND winnerUserId IS NULL", (id,))
        return c.fetchone()


def setup(ctx):
    ctx.add_cog(DiceCog(ctx))
