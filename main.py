import asyncio
import uuid
import random
import aiohttp
import json
from typing import List

from fake_useragent import UserAgent
from aiohttp import ClientTimeout
from aiohttp_socks import ProxyConnector
from better_proxy import Proxy
from tabulate import tabulate
from termcolor import colored


class LayerZero:
    def __init__(self, wallet: str, proxies: List[str]):
        self.wallet = wallet
        self.proxies = proxies
        self.api_url = f'https://www.layerzero.foundation/api/allocation/{self.wallet}'

    async def get_headers(self):
        ua = UserAgent()
        return {
            "Content-Type": 'application/json',
            "User-Agent": ua.random,
            "referer": f'https://www.layerzero.foundation/api/allocation/{self.wallet}',
            "baggage": (
                f"sentry-environment=vercel-production,"
                f"sentry-release=8db980a63760b2e079aa1e8cc36420b60474005a,"
                f"sentry-public_key=7ea9fec73d6d676df2ec73f61f6d88f0,"
                f"sentry-trace_id={uuid.uuid4()}"
            )
        }

    async def send_request(self, method: str, url: str):
        headers = await self.get_headers()
        timeout = ClientTimeout(total=10)

        if not self.proxies:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, headers=headers) as response:
                    return await response.json()

        random.shuffle(self.proxies)

        for proxy in self.proxies:
            proxy = Proxy.from_str(proxy)
            connector = ProxyConnector.from_url(proxy.as_url)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                try:
                    async with session.request(method, url, headers=headers) as response:
                        return await response.json()
                except Exception:
                    continue

    async def get_data(self):
        return await self.send_request('GET', self.api_url)


async def load_file(filename: str) -> List[str]:
    with open(filename, 'r') as file:
        return [line.strip() for line in file.readlines()]


async def process_wallets(wallets: List[str], proxies: List[str]):
    total_zro = 0
    drop_count = 0
    colored_results = []

    print('Собираю информацию о кошельках, может занять несколько минут...')
    print(tabulate([], headers=["Кошелек", "Дали дроп", "Кол-во $ZRO"], tablefmt="plain"))

    for wallet in wallets:
        layer_zero = LayerZero(wallet, proxies)
        try:
            response = await layer_zero.get_data()
        except Exception as e:
            zro_amount = None
            gave_drop = "ОШИБКА"
            result = [wallet, gave_drop, "ОШИБКА"]
            colored_result = [colored(cell, 'yellow') for cell in result]
            colored_results.append(colored_result)
            print(tabulate([colored_result], tablefmt="plain"))
            continue

        if isinstance(response, dict):
            zro_amount = response.get('zroAllocation', {}).get('asString', None)
        else:
            zro_amount = None

        if zro_amount is None:
            gave_drop = "ОШИБКА"
            result = [wallet, gave_drop, "ОШИБКА"]
            colored_result = [colored(cell, 'yellow') for cell in result]
            colored_results.append(colored_result)
        else:
            gave_drop = 'ДА' if float(zro_amount) > 0 else 'НЕТ'
            result = [wallet, gave_drop, zro_amount]

            if gave_drop == 'ДА':
                colored_result = [colored(cell, 'green') for cell in result]
                drop_count += 1
                total_zro += float(zro_amount)
            else:
                colored_result = [colored(cell, 'red') for cell in result]

            colored_results.append(colored_result)

        print(tabulate([colored_result], tablefmt="plain"))

    total_wallets = len(wallets)

    print(f"\nКоличество кошельков: \033[1m{total_wallets}\033[0m")
    print(
        f"Дали дроп: \033[1m{drop_count}/{total_wallets} ({drop_count / total_wallets * 100:.2f}%)\033[0m")
    print(f"Залутал $ZRO: \033[1m{total_zro}\033[0m")
    print(f"При цене токена 3$: ~\033[1m{int(total_zro * 3)}$\033[0m")
    print(f"При цене токена 4$: ~\033[1m{int(total_zro * 4)}$\033[0m")
    print(f"При цене токена 5$: ~\033[1m{int(total_zro * 5)}$\033[0m\n\n")

    if total_wallets > 1 and total_zro <= 50:
        print(f"\033[1mДА И ПОШЕЛ ЭТОТ БРАЙАН НАХУЙ, ДА?\033[0m\n\n")


async def main():
    print("\033[1mOwner by Thor: https://t.me/thor_lab")
    wallets = await load_file('WALLETS.txt')
    proxies = await load_file('PROXIES.txt')

    if not proxies:
        print(colored(
            'Вы запустили чекер без прокси! Если не будет работать, '
            'добавьте их в PROXIES.TXT в любом формате',
            'red'))

    await process_wallets(wallets, proxies)


if __name__ == '__main__':
    asyncio.run(main())
