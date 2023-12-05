import asyncio
from app import create_config

if __name__ == '__main__':
    print("Welcome to My-AVA")

    # Create an event loop
    loop = asyncio.get_event_loop()

    # Run the create_config within the event loop
    loop.run_until_complete(create_config())

    # Close the loop
    loop.close()
