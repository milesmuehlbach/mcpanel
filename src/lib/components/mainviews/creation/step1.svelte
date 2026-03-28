<script lang="ts">
	import * as Field from '$lib/components/ui/field';
	import * as Select from '$lib/components/ui/select'
	// import { Input } from '$lib/components/ui/input';
	import { Checkbox } from '$lib/components/ui/checkbox'
	import { Label } from '$lib/components/ui/label';

	import { onMount } from 'svelte';

	let { incrementStep = () => {} }: { incrementStep?: () => void; } = $props();

	let serverSoftware = $state("mojang");

	let snapshots = $state(false)

	const softwares = [
		{ value: "mojang", label: "Vanilla" },
		{ value: "paper", label: "Paper" }
	];

	const softwareLabel = $derived(
		softwares.find((d) => d.value === serverSoftware)?.label ??
		"Choose server software"
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

	function setNewData() {
		filteredVersions = filterVersionData(serverSoftware, snapshots, await minecraftVersions)
	}

	function filterVersionData(software: string, snapshot: boolean, data: ApiResponse) {
		let filtered = data.components.filter(c =>
			c.component === software
		);
		if (!snapshot) {
			filtered = filtered.filter(c => c.version.startsWith("release-"));
		}
		if (filtered.length === 0) {
			return;
		}
		return filtered;
	}

	async function getMinecraftVersions() {
		try {
			const response = await fetch('/api/v1/components/list?type=server', {
				headers: {
					Authorization: `Bearer ${sessionStorage.getItem('token')}`
				}
			});

			if (!response.ok) {
				throw new Error("response not ok")
			}

			const data: ApiResponse = await response.json();

			return data;

		} catch (error) {
			console.error(error);
			return;
		}
	}

	let minecraftVersions = getMinecraftVersions();
	let filteredVersions = $state(filterVersionData('vanilla', false, minecraftVersions));

	function nextStep(): void {
		incrementStep();
	}

	onMount(() => {

	})
</script>

<form onsubmit={nextStep}>
	<Field.Set>
		<Field.Legend>Software Configuration</Field.Legend>
		<Field.Description>Choose server software and Minecraft version.</Field.Description>
		<Field.Group>
			<Field.Field>
				<Field.Label for="software">Server Software</Field.Label>
				<Select.Root type="single" bind:value={serverSoftware}>
					<Select.Trigger id="department">
						{softwareLabel}
					</Select.Trigger>
					<Select.Content>
						{#each softwares as cursoftware (cursoftware.value)}
							<Select.Item {...cursoftware} />
						{/each}
					</Select.Content>
				</Select.Root>
			</Field.Field>
			<Field.Field>
				<Field.Label for="software">Minecraft Version</Field.Label>
				<Select.Root type="single" bind:value={serverSoftware}>
					<Select.Trigger id="department">
						{softwareLabel}
					</Select.Trigger>
					<Select.Content>
						{#each softwares as cursoftware (cursoftware.value)}
							<Select.Item {...cursoftware} onclick={setNewData}/>
						{/each}
					</Select.Content>
				</Select.Root>
				<div class="flex items-center gap-3">
					<Checkbox id="terms" bind:value={snapshots} onclick={setNewData} />
					<Label for="terms">Show snapshots</Label>
				</div>
			</Field.Field>
		</Field.Group>
	</Field.Set>
</form>