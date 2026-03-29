<script lang="ts">
	import * as Field from '$lib/components/ui/field';
	import * as Select from '$lib/components/ui/select';
	// import { Input } from '$lib/components/ui/input';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Label } from '$lib/components/ui/label';

	import { onMount } from 'svelte';

	let { incrementStep = () => {} }: { incrementStep?: () => void } = $props();

	let serverSoftware = $state('mojang');
	let selectedVersion = $state('');
	let snapshots = $state(false);
	let isLoadingVersions = $state(true);
	let versionsError = $state<string | null>(null);

	const softwares = [
		{ value: 'mojang', label: 'Vanilla' },
		{ value: 'paper', label: 'Paper' }
	];

	const softwareLabel = $derived(
		softwares.find((d) => d.value === serverSoftware)?.label ?? 'Choose server software'
	);

	type Hashes = {
		md5: string | null;
		sha1: string | null;
		sha256: string | null;
	};

	type Component = {
		uid: string;
		type: string; // "server"
		component: string; // "mojang"
		version: string; // "release-26.1" | "snapshot-26.1-rc-3"
		display_type: string;
		display_component: string;
		display_version: string;
		display_name: string;
		hashes: Hashes;
		released_at: string;
	};

	type ApiResponse = {
		message: string;
		components: Component[];
	};

	let minecraftVersions = $state<Component[]>([]);

	const filteredVersions = $derived.by(() => {
		let filtered = minecraftVersions.filter((component) => component.component === serverSoftware);

		if (!snapshots) {
			filtered = filtered.filter((component) => component.version.startsWith('release-'));
		}

		return [...filtered].sort((a, b) => {
			const aTime = Date.parse(a.released_at);
			const bTime = Date.parse(b.released_at);

			if (Number.isNaN(aTime) || Number.isNaN(bTime)) {
				return b.display_version.localeCompare(a.display_version, undefined, {
					numeric: true,
					sensitivity: 'base'
				});
			}

			return bTime - aTime;
		});
	});

	const versionLabel = $derived(
		filteredVersions.find((version) => version.version === selectedVersion)?.display_version ??
			'Choose Minecraft version'
	);

	async function getMinecraftVersions() {
		const response = await fetch('/api/v1/components/list?type=server', {
			headers: {
				Authorization: `Bearer ${sessionStorage.getItem('token')}`
			}
		});

		if (!response.ok) {
			throw new Error('Failed to fetch Minecraft versions');
		}

		const data: ApiResponse = await response.json();
		return data.components;
	}

	async function loadMinecraftVersions() {
		isLoadingVersions = true;
		versionsError = null;

		try {
			minecraftVersions = await getMinecraftVersions();
		} catch (error) {
			console.error(error);
			minecraftVersions = [];
			versionsError = 'Unable to load versions. Please try again.';
		} finally {
			isLoadingVersions = false;
		}
	}

	function nextStep(): void {
		incrementStep();
	}

	onMount(() => {
		void loadMinecraftVersions();
	});
</script>

<form onsubmit={nextStep}>
	<Field.Set>
		<Field.Legend>Software Configuration</Field.Legend>
		<Field.Description>Choose server software and Minecraft version.</Field.Description>
		<Field.Group>
			<Field.Field>
				<Field.Label for="software">Server Software</Field.Label>
				<Select.Root type="single" bind:value={serverSoftware}>
					<Select.Trigger id="software">
						{softwareLabel}
					</Select.Trigger>
					<Select.Content side="bottom" class="max-h-72 [--bits-select-anchor-height:18rem]">
						{#each softwares as cursoftware (cursoftware.value)}
							<Select.Item {...cursoftware} />
						{/each}
					</Select.Content>
				</Select.Root>
			</Field.Field>
			<Field.Field>
				<Field.Label for="minecraft-version">Minecraft Version</Field.Label>
				<Select.Root
					type="single"
					bind:value={selectedVersion}
					disabled={isLoadingVersions || filteredVersions.length === 0}
				>
					<Select.Trigger id="minecraft-version">
						{#if isLoadingVersions}
							Loading versions...
						{:else}
							{versionLabel}
						{/if}
					</Select.Trigger>
					<Select.Content side="bottom" class="max-h-72 [--bits-select-anchor-height:18rem]">
						{#each filteredVersions as version (version.uid)}
							<Select.Item value={version.version} label={version.display_version} />
						{/each}
					</Select.Content>
				</Select.Root>
				{#if versionsError}
					<p class="text-sm text-destructive">{versionsError}</p>
				{:else if !isLoadingVersions && filteredVersions.length === 0}
					<p class="text-sm text-muted-foreground">No versions found for the selected software.</p>
				{/if}
				<div class="flex items-center gap-3">
					<Checkbox id="terms" bind:checked={snapshots} />
					<Label for="terms">Show snapshots</Label>
				</div>
			</Field.Field>
		</Field.Group>
	</Field.Set>
</form>
