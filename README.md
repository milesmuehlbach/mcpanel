# mcpanel

mcpanel is a comprehensive Minecraft server hosting platform.<br>
spanning all server softwares and game versions, we are a open-source self-hostable alternative to platforms like Aternos

### features

- interactive server switching
- full level of customization and ease-of-use as Aternos/Exaroton
- fine-grained permissions system
- open-source
- self-hostable
- we (@TechDudie) personally uses it in his friend group
- free? idfk

### technical details for the hc reviewers

this was a collaborative project in between @milesmuehlbach and @TechDudie.
- svelte frontend w/ adapter-static in SSG, utilizes tailwind v4 & shadcn-svelte for HOLY PEAK ui, handled by @milesmuehlbach
- async fastapi backend and stateful task management, utilizes LOTS of 3p apis/cdns for very peak reasons, handled by @TechDudie

### installation

on Windows, i/actions will build standalone binaries closer to launch<br>
or maybe even an installer that automatically configures services

@milesmuehlbach got docker right?
