<script lang="ts">
	import { serverState } from '$lib/components/mainviews/server/server-state.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Badge } from '$lib/components/ui/badge';
	import Circle from '@lucide/svelte/icons/circle';

	let servername = $derived(serverState.selectedServer?.name ?? 'Unknown Server');
</script>

<div class="flex h-full w-full items-center justify-center bg-background p-4 sm:p-6 lg:p-8">
	<Card.Root class="w-full max-w-4xl">
		<Card.Header class="space-y-3">
			<Card.Title class="text-3xl leading-tight font-black wrap-break-word sm:text-5xl lg:text-6xl">
				{servername}
			</Card.Title>
			<Card.Description class="flex flex-wrap items-center gap-2 text-sm sm:text-base">
				<Badge variant="secondary" class="flex items-center gap-1.5"
					><Circle fill="red" color="red" class="size-2" /> Stopped</Badge
				>
				<Badge variant="secondary">26.1.2</Badge>
				<Badge variant="secondary">Paper</Badge>
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
				<Button class="h-11 bg-emerald-600 text-white hover:bg-emerald-700">Start</Button>
				<Button class="h-11 bg-rose-600 text-white hover:bg-rose-700" disabled>Stop</Button>
				<Button class="h-11 bg-amber-500 text-slate-950 hover:bg-amber-600" disabled>Restart</Button
				>
			</div>
		</Card.Content>
	</Card.Root>
	<Card.Root>
		<Card.Header>
				<Card.Title class="text-2xl font-semibold tracking-tight">Server Logs</Card.Title>
		</Card.Header>
		<Card.Content>

		</Card.Content>
	</Card.Root>
</div>
