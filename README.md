# mcpanel

<p align="center"><i>the absolute best self-hostable minecraft server</i></p>
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/d7acceb8-28fa-4177-ba24-f97d8e80c9a7" />

## info

mcpanel is a comprehensive Minecraft server hosting platform.<br>
spanning all server softwares and game versions, we are a open-source self-hostable alternative to platforms like Aternos.

> We liked the functionality of such panels but were dissapointed to see that there's not a foss version with the same amount of comprehensiveness.<br>
We mainly focus on ease of use; for example we automatically configure RAM sizes based on your computer's ram unless manually configured.<br>
As of now, functionality is limited; currently you can create servers, manage multiple, start them, stop them, restart them, and access a full console. The majority of the work was in managing versions and downloads.

You can access a demo at [mcpanel.milesmuehlbach.com](https://mcpanel.milesmuehlbach.com)
  - username: `demo`
  - password: `password`
  - the main server will be accessible from `those-adding.gl.joinmc.link` when active.

## features

- interactive server switching
- full level of customization and ease-of-use as Aternos/Exaroton
- open-source
- self-hostable
- we (@TechDudie) personally uses it in his friend group
- free

## unimportant details for the hc reviewers

this was a collaborative project in between @milesmuehlbach and @TechDudie.

- svelte frontend w/ adapter-static in SSG, utilizes tailwind v4 & shadcn-svelte for HOLY PEAK ui, handled by @milesmuehlbach
- async fastapi backend and stateful task management, utilizes quite a few 3p apis/cdns for very peak reasons, handled by @TechDudie

## hosting

Only docker is supported in alpha. Windows and standalone binaries will be generated in the future.

Create `docker-compose.yml`:
```yml
services:
  mcpanel:
    image: milesmuehlbach/mcpanel:latest
    container_name: mcpanel
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      PYTHONUNBUFFERED: "1"
    volumes:
      - ./minecraft:/app/minecraft
```

Run `docker compose up`. Web dashboard runs on port `8080`. Your default minecraft server port is `25565`.

## roadmap

mcpanel is still in its infancy. We're just high schoolers with AP exams. With that said, there's *lots* on the roadmap.
 - mod management
 - automatic component updates
 - properties management
 - file browsing
 - logs within file browsing
 - port management
 - admin/user/permissions management
 - server management
 - user side settings
 - potential [playit.gg](https://playit.gg) support
 - Windows/standalone binary support
