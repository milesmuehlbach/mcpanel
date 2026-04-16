<script lang="ts">
	import NoServer from '$lib/components/mainviews/server/components/noserver.svelte';
	import AppSidebar from '$lib/components/mainviews/server/components/panel-sidebar.svelte';
	import type { ServerSubview } from '$lib/components/mainviews/server/server-subroutes';
	import { SERVER_SUBROUTE_LABELS } from '$lib/components/mainviews/server/server-subroutes';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { onMount } from 'svelte';

	let {
		newServer = () => {},
		activeSubview = 'dashboard'
	}: {
		newServer?: () => void;
		activeSubview?: ServerSubview;
	} = $props();

	type ServerListItem = {
		uuid: string;
		name: string;
	};

	function parseServers(data: unknown): ServerListItem[] {
		const rawInstances = Array.isArray(data)
			? data
			: data &&
			typeof data === 'object' &&
			Array.isArray((data as { instances?: unknown }).instances)
				? (data as { instances: unknown[] }).instances
				: [];

		return rawInstances
			.map((instance, index) => {
				if (!instance || typeof instance !== 'object') {
					return null;
				}

				const name = (instance as { name?: unknown }).name;
				if (typeof name !== 'string' || !name.trim()) {
					return null;
				}

				const uuid = (instance as { uuid?: unknown }).uuid;
				return {
					uuid: typeof uuid === 'string' && uuid.trim() ? uuid : `${index}-${name}`,
					name
				};
			})
			.filter((instance): instance is ServerListItem => instance !== null);
	}

	async function getServers(): Promise<ServerListItem[]> {
		const token = sessionStorage.getItem('token');
		if (!token) {
			return [];
		}

		try {
			const response = await fetch('/api/v1/instances/list', {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				return [];
			}

			const data = (await response.json()) as unknown;
			return parseServers(data);
		} catch (error) {
			console.error('Failed to load servers:', error);
			return [];
		}
	}

	let subviewTitle = $derived(SERVER_SUBROUTE_LABELS[activeSubview]);

	let servers = $state<ServerListItem[]>([]);

	onMount(() => {
		servers = getServers();
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
