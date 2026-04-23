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

	let serverStatus = $state(false);
	let serverStateString = $state('stopped');

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
	type LogSegment = {
		text: string;
		style: string;
	};

	type ParsedLogLine = LogSegment[];

	let logs: ParsedLogLine[] = $state([]);
	let logContainer: HTMLDivElement | undefined = $state();
	const MAX_LOG_LINES = 500;
	const ANSI_ESCAPE_PREFIX = '\u001b[';

	const ANSI_BASE_COLORS = [
		'#000000',
		'#800000',
		'#008000',
		'#808000',
		'#000080',
		'#800080',
		'#008080',
		'#c0c0c0'
	] as const;

	const ANSI_BRIGHT_COLORS = [
		'#808080',
		'#ff0000',
		'#00ff00',
		'#ffff00',
		'#0000ff',
		'#ff00ff',
		'#00ffff',
		'#ffffff'
	] as const;

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

	type AnsiStyleState = {
		bold: boolean;
		italic: boolean;
		underline: boolean;
		fg?: string;
		bg?: string;
	};

	function createDefaultStyleState(): AnsiStyleState {
		return {
			bold: false,
			italic: false,
			underline: false,
			fg: undefined,
			bg: undefined
		};
	}

	function clampColorByte(value: number): number {
		return Math.max(0, Math.min(255, value));
	}

	function ansi256ToCssColor(code: number): string {
		const colorCode = clampColorByte(code);

		if (colorCode < 8) {
			return ANSI_BASE_COLORS[colorCode];
		}

		if (colorCode < 16) {
			return ANSI_BRIGHT_COLORS[colorCode - 8];
		}

		if (colorCode < 232) {
			const index = colorCode - 16;
			const r = Math.floor(index / 36);
			const g = Math.floor((index % 36) / 6);
			const b = index % 6;
			const levels = [0, 95, 135, 175, 215, 255];
			return `rgb(${levels[r]}, ${levels[g]}, ${levels[b]})`;
		}

		const gray = 8 + (colorCode - 232) * 10;
		return `rgb(${gray}, ${gray}, ${gray})`;
	}

	function styleStateToCss(state: AnsiStyleState): string {
		const rules: string[] = [];

		if (state.bold) {
			rules.push('font-weight: 700');
		}

		if (state.italic) {
			rules.push('font-style: italic');
		}

		if (state.underline) {
			rules.push('text-decoration: underline');
		}

		if (state.fg) {
			rules.push(`color: ${state.fg}`);
		}

		if (state.bg) {
			rules.push(`background-color: ${state.bg}`);
		}

		return rules.join('; ');
	}

	function applySgrCodes(codes: number[], state: AnsiStyleState): void {
		for (let i = 0; i < codes.length; i++) {
			const code = codes[i];

			if (code === 0) {
				state.bold = false;
				state.italic = false;
				state.underline = false;
				state.fg = undefined;
				state.bg = undefined;
				continue;
			}

			if (code === 1) {
				state.bold = true;
				continue;
			}

			if (code === 22) {
				state.bold = false;
				continue;
			}

			if (code === 3) {
				state.italic = true;
				continue;
			}

			if (code === 23) {
				state.italic = false;
				continue;
			}

			if (code === 4) {
				state.underline = true;
				continue;
			}

			if (code === 24) {
				state.underline = false;
				continue;
			}

			if (code >= 30 && code <= 37) {
				state.fg = ANSI_BASE_COLORS[code - 30];
				continue;
			}

			if (code >= 90 && code <= 97) {
				state.fg = ANSI_BRIGHT_COLORS[code - 90];
				continue;
			}

			if (code === 39) {
				state.fg = undefined;
				continue;
			}

			if (code >= 40 && code <= 47) {
				state.bg = ANSI_BASE_COLORS[code - 40];
				continue;
			}

			if (code >= 100 && code <= 107) {
				state.bg = ANSI_BRIGHT_COLORS[code - 100];
				continue;
			}

			if (code === 49) {
				state.bg = undefined;
				continue;
			}

			if (code === 38 || code === 48) {
				const isForeground = code === 38;
				const mode = codes[i + 1];

				if (mode === 5 && typeof codes[i + 2] === 'number') {
					const color = ansi256ToCssColor(codes[i + 2]);
					if (isForeground) {
						state.fg = color;
					} else {
						state.bg = color;
					}
					i += 2;
					continue;
				}

				if (
					mode === 2 &&
					typeof codes[i + 2] === 'number' &&
					typeof codes[i + 3] === 'number' &&
					typeof codes[i + 4] === 'number'
				) {
					const r = clampColorByte(codes[i + 2]);
					const g = clampColorByte(codes[i + 3]);
					const b = clampColorByte(codes[i + 4]);
					const color = `rgb(${r}, ${g}, ${b})`;

					if (isForeground) {
						state.fg = color;
					} else {
						state.bg = color;
					}
					i += 4;
				}
			}
		}
	}

	function parseAnsiLine(line: string): ParsedLogLine {
		const segments: ParsedLogLine = [];
		const style = createDefaultStyleState();
		let start = 0;

		const pushSegment = (text: string) => {
			if (!text) {
				return;
			}

			const segmentStyle = styleStateToCss(style);
			const previous = segments[segments.length - 1];
			if (previous && previous.style === segmentStyle) {
				previous.text += text;
				return;
			}

			segments.push({
				text,
				style: segmentStyle
			});
		};

		while (start < line.length) {
			const escapeIndex = line.indexOf(ANSI_ESCAPE_PREFIX, start);
			if (escapeIndex === -1) {
				break;
			}

			pushSegment(line.slice(start, escapeIndex));

			const sequenceStart = escapeIndex + ANSI_ESCAPE_PREFIX.length;
			const sequenceEnd = line.indexOf('m', sequenceStart);
			if (sequenceEnd === -1) {
				start = escapeIndex;
				break;
			}

			const sequence = line.slice(sequenceStart, sequenceEnd).trim();
			const codes =
				sequence === ''
					? [0]
					: sequence
							.split(';')
							.map((part) => Number.parseInt(part, 10))
							.filter((code) => Number.isFinite(code));

			applySgrCodes(codes, style);
			start = sequenceEnd + 1;
		}

		pushSegment(line.slice(start));

		if (segments.length === 0) {
			segments.push({
				text: '',
				style: ''
			});
		}

		return segments;
	}

	function appendLog(line: string) {
		logs.push(parseAnsiLine(line));
		if (logs.length > MAX_LOG_LINES) {
			logs.shift();
		}
	}

	$effect(() => {
		if (logs.length > 0 && logContainer) {
			logContainer.scrollTop = logContainer.scrollHeight;
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
									<p class="break-words whitespace-pre-wrap text-foreground/90">
										{#each line as segment, j (`${i}-${j}`)}
											<span style={segment.style}>{segment.text}</span>
										{/each}
									</p>
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
							disabled={serverStateString !== 'running'}
						/>
						<Button
							type="submit"
							variant="outline"
							size="icon"
							aria-label="Send command"
							disabled={serverStateString !== 'running'}
						>
							<SendHorizontal class="size-4" />
						</Button>
					</form>
				</Card.Footer>
			</Card.Root>
		</div>
	</div>
</div>
