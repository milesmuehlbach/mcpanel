<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import AppSidebar from '$lib/components/panel-sidebar.svelte';
	import NoServer from '$lib/components/noserver.svelte';
	import { Separator } from "$lib/components/ui/separator/index.js";
</script>

<Sidebar.Provider>
	<AppSidebar />
	<Sidebar.Inset>
		<div
			class="sticky top-0 z-20 m-2 flex items-center gap-2 rounded-md border border-border/70 bg-card/70 px-2 py-1.5 backdrop-blur supports-[backdrop-filter]:bg-card/60"
		>
			<Sidebar.Trigger class="size-8 shrink-0 bg-transparent" />
			<Separator orientation="vertical" />
			<h1 class="text-sm font-semibold tracking-tight text-foreground">MCPanel</h1>
		</div>
		<NoServer />
	</Sidebar.Inset>
</Sidebar.Provider>
