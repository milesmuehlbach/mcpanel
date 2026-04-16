<script lang="ts">
	import { serverState } from '$lib/components/mainviews/server/server-state.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Badge } from '$lib/components/ui/badge';
	import Circle from '@lucide/svelte/icons/circle';
	import { toast } from 'svelte-sonner';
	import { onMount } from 'svelte';

	let servername = $derived(serverState.selectedServer?.name ?? 'Unknown Server');

	let serverStatus = $state(false);

	async function reloadServerState(): Promise<void> {
		const token = sessionStorage.getItem('token');
		try {
			const response = await fetch(`/api/v1/instances/${serverState.selectedServer?.uuid}/status`, {
				method: 'GET',
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				console.error('Failed to reload server state:', response.statusText);
				toast.error('Failed to reload server state: ' + response.statusText);
				return;
			}

			const data = await response.json();
			serverStatus = data.running;
			await serverState.loadServers();
		} catch (error) {
			console.error('Error reloading server state:', error);
			toast.error('Error reloading server state: ' + error);
		}
	}

	async function restartServer(): Promise<void> {
		if (!serverState.selectedServer) {
			return;
		}

		const token = sessionStorage.getItem('token');
		try {
			const response = await fetch(`/api/v1/instances/${serverState.selectedServer.uuid}/restart`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				console.error('Failed to restart server:', response.statusText);
				toast.error('Failed to restart server: ' + response.statusText);
				return;
			}
			await reloadServerState();
		} catch (error) {
			console.error('Error restarting server:', error);
			toast.error('Error restarting server: ' + error);
		}
	}

	async function stopServer(): Promise<void> {
		if (!serverState.selectedServer) {
			return;
		}

		const token = sessionStorage.getItem('token');
		try {
			const response = await fetch(`/api/v1/instances/${serverState.selectedServer.uuid}/stop`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				console.error('Failed to stop server:', response.statusText);
				toast.error('Failed to stop server: ' + response.statusText);
				return;
			}
			await reloadServerState();
		} catch (error) {
			console.error('Error stopping server:', error);
			toast.error('Error stopping server: ' + error);
		}
	}

	async function startServer(): Promise<void> {
		if (!serverState.selectedServer) {
			return;
		}

		const token = sessionStorage.getItem('token');
		try {
			const response = await fetch(`/api/v1/instances/${serverState.selectedServer.uuid}/start`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				console.error('Failed to start server:', response.statusText);
				toast.error('Failed to start server: ' + response.statusText);
				return;
			}
			await reloadServerState();
		} catch (error) {
			console.error('Error starting server:', error);
			toast.error('Error starting server: ' + error);
		}
	}

	$effect(() => {
		if (serverState.selectedServer?.uuid) {
			void reloadServerState();
		}
	});
</script>

<div
	class="flex h-full w-full flex-col items-center justify-center gap-6 bg-background p-4 sm:p-6 lg:p-8"
>
	<Card.Root class="w-full max-w-4xl">
		<Card.Header class="space-y-3">
			<Card.Title class="text-3xl leading-tight font-black break-words sm:text-5xl lg:text-6xl">
				{servername}
			</Card.Title>
			<Card.Description class="flex flex-wrap items-center gap-2 text-sm sm:text-base">
				<Badge variant="secondary" class="flex items-center gap-1.5">
					<Circle
						fill={serverStatus ? 'green' : 'red'}
						color={serverStatus ? 'green' : 'red'}
						class="size-2"
					/>
					{serverStatus ? 'Running' : 'Stopped'}
				</Badge>
				<Badge variant="secondary">26.1.2</Badge>
				<Badge variant="secondary">Paper</Badge>
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
				<Button
					class="h-11 bg-emerald-600 text-white hover:bg-emerald-700"
					onclick={startServer}
					disabled={serverStatus === true}>Start</Button
				>
				<Button
					class="h-11 bg-rose-600 text-white hover:bg-rose-700"
					onclick={stopServer}
					disabled={serverStatus === false}>Stop</Button
				>
				<Button
					class="h-11 bg-amber-500 text-slate-950 hover:bg-amber-600"
					onclick={restartServer}
					disabled={serverStatus === false}>Restart</Button
				>
			</div>
		</Card.Content>
	</Card.Root>
	{#if serverStatus}
		<Card.Root class="w-full max-w-4xl">
			<Card.Header>
				<Card.Title class="text-2xl font-semibold tracking-tight">Server Logs</Card.Title>
			</Card.Header>
			<Card.Content>
				<div class="w-full border-t border-muted pt-4">
					<div class="h-64 w-full overflow-y-auto rounded-md bg-muted p-4">
						<p class="text-sm text-muted-foreground">Server logs will appear here.</p>
					</div>
				</div>
			</Card.Content>
			<Card.Footer class="flex justify-end">
				<Button variant="outline" size="sm" disabled>Go to Console</Button>
			</Card.Footer>
		</Card.Root>
	{/if}
</div>