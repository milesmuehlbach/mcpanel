<script lang="ts">
	import { serverState } from '$lib/components/mainviews/server/server-state.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Badge } from '$lib/components/ui/badge';
	import Circle from '@lucide/svelte/icons/circle';
	import Terminal from '@lucide/svelte/icons/terminal'
	import { toast } from 'svelte-sonner';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { onMount, untrack } from 'svelte';
	import { navigate } from 'svelte5-router';

	let servername = $derived(serverState.selectedServer?.name ?? 'Unknown Server');

	let serverStatus = $state(false);
	let serverStateString = $state('stopped');

	let consoleAbortController: AbortController | undefined;
	let logs: string[] = $state([]);
	let logContainer: HTMLDivElement | undefined = $state();
	const MAX_LOG_LINES = 500;

	onMount(() => {
		const interval = setInterval(reloadServerState, 1000);
		return () => {
			clearInterval(interval);
		};
	});

	function appendLog(line: string) {
		logs.push(line);
		if (logs.length > MAX_LOG_LINES) {
			logs.shift();
		}
	}

	function scrollToBottom() {
		if (logContainer) {
			logContainer.scrollTop = logContainer.scrollHeight;
		}
	}

	$effect(() => {
		if (logs.length > 0) {
			scrollToBottom();
		}
	});

	function teardownConsoleStream() {
		if (consoleAbortController) {
			consoleAbortController.abort();
			consoleAbortController = undefined;
		}
	}

	function parseEventDataValue(line: string): string {
		const value = line.slice(5);
		return value.startsWith(' ') ? value.slice(1) : value;
	}

	async function setupConsoleStream(uuid: string, token: string) {
		teardownConsoleStream();

		const abortController = new AbortController();
		consoleAbortController = abortController;

		try {
			const response = await fetch(`/api/v1/instances/${uuid}/console`, {
				method: 'GET',
				headers: {
					Authorization: `Bearer ${token}`,
					Accept: 'text/event-stream'
				},
				signal: abortController.signal
			});

			if (!response.ok) {
				console.error('Console stream request failed:', response.status, response.statusText);
				if (response.status === 401) {
					toast.error('Console stream unauthorized (401). Please log in again.');
				}
				return;
			}

			if (!response.body) {
				console.error('Console stream did not return a readable body');
				return;
			}

			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';
			let eventData: string[] = [];

			const flushEvent = () => {
				if (eventData.length > 0) {
					appendLog(eventData.join('\n'));
					eventData = [];
				}
			};

			try {
				while (true) {
					const { value, done } = await reader.read();
					if (done) break;

					buffer += decoder.decode(value, { stream: true });
					const lines = buffer.split('\n');
					buffer = lines.pop() ?? '';

					for (const line of lines) {
						const normalizedLine = line.replace(/\r$/, '');
						if (normalizedLine === '') {
							flushEvent();
							continue;
						}

						if (normalizedLine.startsWith('data:')) {
							eventData.push(parseEventDataValue(normalizedLine));
						}
					}
				}

				buffer += decoder.decode();
				if (buffer.length > 0) {
					const normalizedLine = buffer.replace(/\r$/, '');
					if (normalizedLine.startsWith('data:')) {
						eventData.push(parseEventDataValue(normalizedLine));
					}
				}
				flushEvent();
			} catch (error) {
				if (!(error instanceof DOMException && error.name === 'AbortError')) {
					console.error('Console stream failed while reading:', error);
				}
			} finally {
				reader.releaseLock();
			}
		} catch (error) {
			if (!(error instanceof DOMException && error.name === 'AbortError')) {
				console.error('Console stream setup failed:', error);
			}
		} finally {
			if (consoleAbortController === abortController) {
				consoleAbortController = undefined;
			}
		}
	}

	$effect(() => {
		const uuid = serverState.selectedServer?.uuid;
		const state = serverStateString;
		if (!uuid || state === 'stopped') {
			teardownConsoleStream();
			return;
		}

		const token = sessionStorage.getItem('token');
		if (!token) {
			console.error('Missing auth token for console stream');
			toast.error('Missing auth token. Please log in again.');
			return;
		}

		void setupConsoleStream(uuid, token);
		return () => {
			teardownConsoleStream();
		};
	});

	async function reloadServerState(): Promise<void> {
		const selectedServer = serverState.selectedServer;
		if (!selectedServer) {
			serverStatus = false;
			serverStateString = 'stopped';
			return;
		}

		const token = sessionStorage.getItem('token');
		try {
			const response = await fetch(`/api/v1/instances/${selectedServer.uuid}/status`, {
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
			serverStateString = data.status;
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
		const selectedServer = serverState.selectedServer;
		try {
			const response = await fetch(`/api/v1/instances/${selectedServer.uuid}/start`, {
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

			serverStateString = 'starting';
			if (token) {
				void setupConsoleStream(selectedServer.uuid, token);
			}
			await reloadServerState();
		} catch (error) {
			console.error('Error starting server:', error);
			toast.error('Error starting server: ' + error);
		}
	}

	$effect(() => {
		untrack(() => {
			void reloadServerState();
		});
	});
</script>

<div class="flex h-full w-full items-center justify-center overflow-y-auto bg-background">
	<div class="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
		<div>
			<Card.Root class="w-full">
				<Card.Header class="space-y-3">
					<Card.Title class="text-3xl leading-tight font-black break-words sm:text-5xl lg:text-6xl">
						{servername}
					</Card.Title>
					<Card.Description class="flex flex-wrap items-center gap-2 text-sm sm:text-base">
						<Badge variant="secondary" class="flex items-center gap-1.5">
							{#if serverStateString === 'running' || serverStateString === 'stopped'}
								<Circle
									fill={serverStatus ? 'green' : 'red'}
									color={serverStatus ? 'green' : 'red'}
									class="size-2"
								/>
							{:else}
								<Spinner class="size-2" />
							{/if}
							{serverStateString.charAt(0).toUpperCase() + serverStateString.slice(1)}
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
							disabled={!(serverStateString === 'stopped')}>Start</Button
						>
						<Button
							class="h-11 bg-rose-600 text-white hover:bg-rose-700"
							onclick={stopServer}
							disabled={!(serverStateString === 'running')}>Stop</Button
						>
						<Button
							class="h-11 bg-amber-500 text-slate-950 hover:bg-amber-600"
							onclick={restartServer}
							disabled={!(serverStateString === 'running')}>Restart</Button
						>
					</div>
				</Card.Content>
			</Card.Root>
		</div>

		{#if serverStateString !== 'stopped'}
			<div class="w-full">
				<Card.Root class="w-full">
					<Card.Header>
						<Card.Title class="text-2xl font-semibold tracking-tight">Server Logs</Card.Title>
					</Card.Header>
					<Card.Content>
						<div class="w-full border-t border-muted pt-4">
							<div
								bind:this={logContainer}
								class="h-64 w-full overflow-y-auto rounded-md bg-muted p-4"
							>
								{#each logs as line, i (i)}
									<p class="text-sm text-muted-foreground">{line}</p>
								{/each}
							</div>
						</div>
					</Card.Content>
					<Card.Footer class="flex justify-end">
						<Button
							variant="outline"
							size="sm"
							onclick={() => {
								navigate(`/servers/${serverState.selectedServerUuid}/console`);
							}}><Terminal />Go to Console</Button
						>
					</Card.Footer>
				</Card.Root>
			</div>
		{/if}
	</div>
</div>
