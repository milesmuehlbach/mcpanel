<script lang="ts">
	import NoServer from '$lib/components/mainviews/server/components/noserver.svelte';
	import AppSidebar from '$lib/components/mainviews/server/components/panel-sidebar.svelte';
	import type { ServerSubview } from '$lib/components/mainviews/server/server-subroutes';
	import { SERVER_SUBROUTE_LABELS } from '$lib/components/mainviews/server/server-subroutes';
	import { serverState } from '$lib/components/mainviews/server/server-state.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { navigate } from 'svelte5-router';
	import { onMount } from 'svelte';

	let {
		newServer = () => {},
		activeSubview = 'dashboard',
		selectedServerUuid = null
	}: {
		newServer?: () => void;
		activeSubview?: ServerSubview;
		selectedServerUuid?: string | null;
	} = $props();

	let subviewTitle = $derived(SERVER_SUBROUTE_LABELS[activeSubview]);
	let servers = $derived(serverState.servers);

	$effect(() => {
		if (selectedServerUuid) {
			serverState.selectedServerUuid = selectedServerUuid;
		}
	});

	onMount(() => {
		void (async () => {
			await serverState.loadServers();

			const canonicalServerUuid = serverState.selectedServerUuid;
			if (!canonicalServerUuid) {
				return;
			}

			if (selectedServerUuid !== canonicalServerUuid) {
				navigate(`/servers/${canonicalServerUuid}/${activeSubview}`, { replace: true });
			}
		})();
	});
</script>

<Sidebar.Provider>
	<AppSidebar {newServer} {activeSubview} />
	<Sidebar.Inset>
		{#if servers.length === 0}
			<NoServer {newServer} />
		{:else}
			<div class="flex h-full w-full items-center justify-center p-6">
				<div class="text-center">
					<h2 class="text-2xl font-semibold tracking-tight">{subviewTitle}</h2>
					<p class="mt-2 text-sm text-muted-foreground">This view is coming soon.</p>
				</div>
			</div>
		{/if}
	</Sidebar.Inset>
</Sidebar.Provider>
