async def endpoint(user, client):
    profile = user.profile
    return await client.fetch(profile)
