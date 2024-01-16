from app import create_config
import asyncio

if __name__ == '__main__':
    print("Welcome to My-AVA")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_config())
    loop.close()