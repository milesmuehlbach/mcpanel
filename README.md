# mcpanel

mcpanel is a comprehensive Minecraft server hosting platform.<br>
spanning all server softwares and game versions (editor note: rn its just paper and vanilla but we're working on support for more), we are a open-source self-hostable alternative to comprehensive hosting platforms like Aternos. We liked the functionality of such panels but were dissapointed to see that there's not a foss version with the same amount of comprehensiveness.<br>
We mainly focus on ease of use; for example we automatically configure RAM sizes based on your computer's ram unless manually configured.<br>
As of now, functionality is limited; currently you can create servers, manage multiple, start them, stop them, restart them, and access a full console. The majority of the work was in managing versions and downloads.

you can access a demo at [mcpanel.milesmuehlbach.com](https://mcpanel.milesmuehlbach.com)
### features

- interactive server switching
- full level of customization and ease-of-use as Aternos/Exaroton
- open-source
- self-hostable
- we (@TechDudie) personally uses it in his friend group
- free

### technical details for the hc reviewers

this was a collaborative project in between @milesmuehlbach and @TechDudie.

- svelte frontend w/ adapter-static in SSG, utilizes tailwind v4 & shadcn-svelte for HOLY PEAK ui, handled by @milesmuehlbach
- async fastapi backend and stateful task management, utilizes LOTS of 3p apis/cdns for very peak reasons, handled by @TechDudie

### hosting
This is a beta release, and for hosting right now we mainly have docker support. Windows/standalone binary support is in the roadmap.
Copy this `docker-compose.yml` into a new file.
```yml
services:
  mcpanel:
    image: milesmuehlbach/mcpanel:lastest
    container_name: mcpanel
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      PYTHONUNBUFFERED: "1"
    volumes:
      - ./minecraft:/app/minecraft
```
run `docker compose up` and wait for the server to run! It'll be running on port `8080`.
The default server port is `25565`.

# roadmap
This project is still in its infancy. With that said, there's *lots* on the roadmap.
 - automatic component updates
 - properties management
 - file browsing
 - logs within file browsing
 - port management (eg allowing for multiple ports and the like for geyser/vc etc)
 - admin/user/permissions management
 - server management (ports, networking stuff, component/software management, etc)
 - user side settings (?) reset password etc
 - potential [playit.gg](https://playit.gg) support
 - standalone binary support (not just running on docker)
 
