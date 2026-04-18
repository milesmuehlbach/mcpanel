<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { serverState } from '$lib/components/mainviews/server/server-state.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import * as Card from '$lib/components/ui/card';
	import SendHorizontal from '@lucide/svelte/icons/send-horizontal';
	import type { Action } from 'svelte/action';
	import { onMount } from 'svelte';
	import Circle from '@lucide/svelte/icons/circle';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Badge } from '$lib/components/ui/badge';

	let viewportHeight = $state(0);
	let consoleCardHeight = $state(0);
	const consoleTopMargin = 24;

	let serverStatus = $state(false)
	let serverStateString = $state('stopped')

	onMount(() => {
		const interval = setInterval(reloadServerState, 1000);
		return () => {
			clearInterval(interval);
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


	const trackCardHeight: Action<HTMLDivElement> = (node) => {
		const updateHeight = () => {
			consoleCardHeight = node.offsetHeight;
		};

		updateHeight();
		const observer = new ResizeObserver(updateHeight);
		observer.observe(node);

		return {
			destroy() {
				observer.disconnect();
			}
		};
	};

	const consoleTopSpacer = $derived(
		Math.max(consoleTopMargin, viewportHeight / 2 - consoleCardHeight / 2 - consoleTopMargin)
	);

	let consoleAbortController: AbortController | undefined;
	let logs: string[] = $state([]);
	let logContainer: HTMLDivElement | undefined = $state();
	const MAX_LOG_LINES = 500;

	let command: string = $state('');

	async function handleSubmit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		await sendCommand();
	}

	async function sendCommand(): Promise<void> {
		const trimmedCommand = command.trim();
		if (!trimmedCommand) {
			return;
		}

		try {
			const response = await fetch(`/api/v1/instances/${serverState.selectedServerUuid}/console`, {
				method: 'POST',
				body: JSON.stringify({ command: trimmedCommand }),
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${sessionStorage.getItem('token')}`
				}
			});
			if (!response.ok) {
				console.error('Failed to send command:', response.statusText);
				toast.error('Failed to send command: ' + response.statusText);
				return;
			}
			command = '';
			return;
		} catch (error) {
			console.error('Failed to send command:', error);
			toast.error('Failed to send command: ' + error);
			return;
		}
	}

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

	$effect(() => {
		const uuid = serverState.selectedServer?.uuid;
		if (!uuid) return;

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
</script>

<svelte:window bind:innerHeight={viewportHeight} />

<div class="h-full w-full overflow-y-auto bg-background">
	<div class="mx-auto flex w-full max-w-4xl flex-col px-4 pb-8 sm:px-6 lg:px-8">
		<div style={`height: ${consoleTopSpacer.toFixed(2)}px;`} aria-hidden="true"></div>

		<div class="overflow-hidden" use:trackCardHeight>
			<Card.Root class="w-full">
				<Card.Header class="space-y-2">
					<Card.Title class="text-2xl font-semibold tracking-tight">Console</Card.Title>
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
				</Card.Header>
				<Card.Content>
					<div class="w-full border-t border-muted pt-4">
						<div
							bind:this={logContainer}
							class="h-[55vh] min-h-72 w-full overflow-y-auto rounded-md border border-border/80 bg-muted/35 p-3 font-mono text-xs leading-5 sm:text-sm"
						>
							{#if logs.length === 0}
								<p class="text-muted-foreground/80">Waiting for console output...</p>
							{:else}
								{#each logs as line, i (i)}
									<p class="break-words whitespace-pre-wrap text-foreground/90">{line}</p>
								{/each}
							{/if}
						</div>
					</div>
				</Card.Content>
				<Card.Footer>
					<form class="flex w-full items-center gap-2" onsubmit={handleSubmit}>
						<Input
							bind:value={command}
							placeholder="Enter command..."
							class="h-10 flex-1 font-mono"
							disabled={!serverStatus}
						/>
						<Button type="submit" variant="outline" size="icon" aria-label="Send command" disabled={!serverStatus}>
							<SendHorizontal class="size-4" />
						</Button>
					</form>
				</Card.Footer>
			</Card.Root>
		</div>
	</div>
</div>
