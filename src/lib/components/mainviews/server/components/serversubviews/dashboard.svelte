<script lang="ts">
	import { serverState } from '$lib/components/mainviews/server/server-state.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Badge } from '$lib/components/ui/badge';
	import Circle from '@lucide/svelte/icons/circle';
	import { toast } from 'svelte-sonner';
	import { quintOut } from 'svelte/easing';
	import { Tween } from 'svelte/motion';
	import type { Action } from 'svelte/action';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { untrack } from 'svelte';

	let servername = $derived(serverState.selectedServer?.name ?? 'Unknown Server');

	let serverStatus = $state(false);
	let viewportHeight = $state(0);
	let controlsCardHeight = $state(0);
	const controlsTopMargin = 24;

	let consoleAbortController: AbortController | undefined;
	let logs: string[] = $state([]);
	let logContainer: HTMLDivElement | undefined = $state();
	const MAX_LOG_LINES = 500;

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

	const trackCardHeight: Action<HTMLDivElement> = (node) => {
		const updateHeight = () => {
			controlsCardHeight = node.offsetHeight;
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

	const logReveal = Tween.of(() => (serverStatus ? 1 : 0), {
		duration: 320,
		easing: quintOut
	});

	const controlsTopSpacer = $derived(
		Math.max(controlsTopMargin, viewportHeight / 2 - controlsCardHeight / 2 - controlsTopMargin)
	);
	const logsMotionStyle = $derived.by(() => {
		const progress = logReveal.current;
		const maxHeight = 480 * progress;
		const translateY = 14 * (1 - progress);
		const marginTop = 24 * progress;
		const opacity = Math.max(0, (progress - 0.2) / 0.8);

		return `max-height: ${maxHeight.toFixed(2)}px; opacity: ${opacity.toFixed(3)}; transform: translate3d(0, ${translateY.toFixed(2)}px, 0); margin-top: ${marginTop.toFixed(2)}px; pointer-events: ${progress > 0.02 ? 'auto' : 'none'}; visibility: ${progress > 0 ? 'visible' : 'hidden'};`;
	});

	async function reloadServerState(): Promise<void> {
		const selectedServer = serverState.selectedServer;
		if (!selectedServer) {
			serverStatus = false;
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
		untrack(() => {
			void reloadServerState();
		});
	});
</script>

<svelte:window bind:innerHeight={viewportHeight} />

<div class="h-full w-full overflow-y-auto bg-background">
	<div class="mx-auto flex w-full max-w-4xl flex-col px-4 pb-8 sm:px-6 lg:px-8">
		<div style={`height: ${controlsTopSpacer.toFixed(2)}px;`} aria-hidden="true"></div>

		<div use:trackCardHeight>
			<Card.Root class="w-full">
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
		</div>

		<div
			class="overflow-hidden will-change-[max-height,opacity,transform,margin-top]"
			style={logsMotionStyle}
		>
			<Card.Root class="w-full" aria-hidden={!serverStatus}>
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
					<Tooltip.Root>
						<Tooltip.Trigger>
							<Button variant="outline" size="sm" disabled>Go to Console</Button>
						</Tooltip.Trigger>
						<Tooltip.Content>
							<p>Currently disabled as Console has not been implemented yet.</p>
						</Tooltip.Content>
					</Tooltip.Root>
				</Card.Footer>
			</Card.Root>
		</div>
	</div>
</div>
