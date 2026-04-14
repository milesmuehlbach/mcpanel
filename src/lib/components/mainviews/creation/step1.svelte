<script lang="ts">
	import * as Field from '$lib/components/ui/field';
	import * as Select from '$lib/components/ui/select';
	import * as Accordion from '$lib/components/ui/accordion';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { Input } from '$lib/components/ui/input';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Label } from '$lib/components/ui/label';
	import { Button, buttonVariants } from '$lib/components/ui/button';
	import { cn } from '$lib/utils';

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

	type RecommendedJreResponse = {
		message: string;
		component: string;
	};

	let minecraftVersions = $state<Component[]>([]);
	let jreComponents = $state<Component[]>([]);
	let isLoadingJres = $state(true);
	let jresError = $state<string | null>(null);
	let useRecommendedRuntime = $state(true);
	let selectedRuntimeType = $state('');
	let selectedRuntimeVersion = $state('');
	let recommendedJreUid = $state<string | null>(null);
	let isLoadingRecommendedJre = $state(false);
	let recommendedJreError = $state<string | null>(null);
	let recommendedRequestCounter = 0;

	function sortComponentsByRelease(components: Component[]): Component[] {
		return [...components].sort((a, b) => {
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
	}

	const filteredVersions = $derived.by(() => {
		let filtered = minecraftVersions.filter((component) => component.component === serverSoftware);

		if (!snapshots) {
			filtered = filtered.filter((component) => component.version.startsWith('release-'));
		}

		return sortComponentsByRelease(filtered);
	});

	const versionToComponent = $derived.by(() => {
		return Object.fromEntries(
			filteredVersions.map((component) => [component.version, component])
		) as Record<string, Component>;
	});

	const jreUidToComponent = $derived.by(() => {
		return Object.fromEntries(
			jreComponents.map((component) => [component.uid, component])
		) as Record<string, Component>;
	});

	const selectedServerComponent = $derived(versionToComponent[selectedVersion] ?? null);
	const selectedServerUid = $derived(selectedServerComponent?.uid ?? null);

	const versionLabel = $derived(
		filteredVersions.find((version) => version.version === selectedVersion)?.display_version ??
			'Choose Minecraft version'
	);

	const runtimeTypeOptions = $derived.by(() => {
		const byType: Record<string, string> = {};

		for (const runtime of jreComponents) {
			if (!byType[runtime.component]) {
				byType[runtime.component] = runtime.display_component || runtime.component;
			}
		}

		return Object.entries(byType)
			.map(([value, label]) => ({ value, label }))
			.sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: 'base' }));
	});

	const runtimeTypeLabel = $derived(
		runtimeTypeOptions.find((runtimeType) => runtimeType.value === selectedRuntimeType)?.label ??
			'Choose Java runtime type'
	);

	const runtimeVersionsForSelectedType = $derived.by(() => {
		const filtered = jreComponents.filter(
			(component) => component.component === selectedRuntimeType
		);
		return sortComponentsByRelease(filtered);
	});

	const runtimeVersionLabel = $derived(
		runtimeVersionsForSelectedType.find((component) => component.version === selectedRuntimeVersion)
			?.display_version ?? 'Choose Java runtime version'
	);

	const selectedManualRuntimeComponent = $derived(
		runtimeVersionsForSelectedType.find(
			(component) => component.version === selectedRuntimeVersion
		) ?? null
	);

	const recommendedRuntimeComponent = $derived(
		recommendedJreUid ? (jreUidToComponent[recommendedJreUid] ?? null) : null
	);

	const manualRuntimeUid = $derived(selectedManualRuntimeComponent?.uid ?? null);
	const effectiveRuntimeUid = $derived(
		useRecommendedRuntime ? recommendedJreUid : manualRuntimeUid
	);

	function parseJreUid(uid: string | null): { component: string; version: string } | null {
		if (!uid) {
			return null;
		}

		const parts = uid.split(':');

		if (parts.length !== 3 || parts[0] !== 'jre' || !parts[1] || !parts[2]) {
			return null;
		}

		return { component: parts[1], version: parts[2] };
	}

	const recommendedRuntimeFallback = $derived(parseJreUid(recommendedJreUid));

	const recommendedRuntimeLabel = $derived.by(() => {
		if (recommendedRuntimeComponent) {
			return recommendedRuntimeComponent.display_name;
		}

		if (recommendedRuntimeFallback) {
			return `${recommendedRuntimeFallback.component} ${recommendedRuntimeFallback.version}`;
		}

		return null;
	});

	// const manualRuntimeLabel = $derived(selectedManualRuntimeComponent?.display_name ?? null); // not needed anymore, keeping around if i do

	async function getRecommendedJre(serveruid: string): Promise<string> {
		const response = await fetch('/api/v1/components/get_recommended_jre?server_uid=' + serveruid, {
			headers: {
				Authorization: `Bearer ${sessionStorage.getItem('token')}`
			}
		});

		if (!response.ok) {
			throw new Error('Failed to fetch recommended JRE');
		}

		const data: RecommendedJreResponse = await response.json();
		return data.component;
	}

	async function getJreComponents() {
		const response = await fetch('/api/v1/components/list?type=jre', {
			headers: {
				Authorization: `Bearer ${sessionStorage.getItem('token')}`
			}
		});

		if (!response.ok) {
			throw new Error('Failed to fetch Java runtimes');
		}

		const data: ApiResponse = await response.json();
		return data.components;
	}

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

	async function loadJreComponents() {
		isLoadingJres = true;
		jresError = null;

		try {
			jreComponents = await getJreComponents();
			syncRuntimeSelection();
		} catch (error) {
			console.error(error);
			jreComponents = [];
			jresError = 'Unable to load Java runtimes. Please try again.';
		} finally {
			isLoadingJres = false;
		}
	}

	function nextStep(event: SubmitEvent): void {
		event.preventDefault();
	}

	function setRuntimeType(value: string): void {
		selectedRuntimeType = value;
		syncRuntimeSelection();
	}

	function setRuntimeVersion(value: string): void {
		selectedRuntimeVersion = value;
	}

	function syncRuntimeSelection(): void {
		const runtimeTypes = runtimeTypeOptions;

		if (runtimeTypes.length === 0) {
			selectedRuntimeType = '';
			selectedRuntimeVersion = '';
			return;
		}

		if (!runtimeTypes.some((runtimeType) => runtimeType.value === selectedRuntimeType)) {
			selectedRuntimeType = runtimeTypes[0].value;
		}

		const versionsForType = sortComponentsByRelease(
			jreComponents.filter((component) => component.component === selectedRuntimeType)
		);

		if (versionsForType.length === 0) {
			selectedRuntimeVersion = '';
			return;
		}

		if (!versionsForType.some((version) => version.version === selectedRuntimeVersion)) {
			selectedRuntimeVersion = versionsForType[0].version;
		}
	}

	function setServerSoftware(value: string): void {
		serverSoftware = value;
		syncSelectedVersionAndRecommendedRuntime();
	}

	function setSelectedVersion(value: string): void {
		selectedVersion = value;
		void refreshRecommendedRuntime();
	}

	function setSnapshots(value: boolean): void {
		snapshots = value;
		syncSelectedVersionAndRecommendedRuntime();
	}

	function syncSelectedVersionAndRecommendedRuntime(): void {
		if (!filteredVersions.some((version) => version.version === selectedVersion)) {
			selectedVersion = '';
		}

		void refreshRecommendedRuntime();
	}

	async function refreshRecommendedRuntime(): Promise<void> {
		const serverUid = selectedServerUid;
		const requestId = ++recommendedRequestCounter;

		recommendedJreError = null;
		recommendedJreUid = null;

		if (!serverUid) {
			isLoadingRecommendedJre = false;
			return;
		}

		isLoadingRecommendedJre = true;

		try {
			const runtimeUid = await getRecommendedJre(serverUid);

			if (requestId !== recommendedRequestCounter) {
				return;
			}

			recommendedJreUid = runtimeUid;
		} catch (error) {
			if (requestId !== recommendedRequestCounter) {
				return;
			}

			console.error(error);
			recommendedJreError = 'Unable to fetch recommended Java runtime for this server version.';
		} finally {
			if (requestId !== recommendedRequestCounter) {
				return;
			}

			isLoadingRecommendedJre = false;
		}
	}

	function submitComponentInstallation(): void {
		if (!selectedVersion) {
			return;
		}

		const serverComponent = versionToComponent[selectedVersion];
		const runtimeComponent = effectiveRuntimeUid ? jreUidToComponent[effectiveRuntimeUid] : null;

		if (!serverComponent) {
			return;
		}

		const installationData = {
			server: {
				component_uid: serverComponent.uid,
				component_version: serverComponent.version,
				hashes: serverComponent.hashes
			},
			runtime: runtimeComponent
				? {
						component_uid: runtimeComponent.uid,
						component_version: runtimeComponent.version,
						hashes: runtimeComponent.hashes
					}
				: null
		};

		sessionStorage.setItem('installationData', JSON.stringify(installationData));
		incrementStep();
	}

	onMount(() => {
		sessionStorage.removeItem('installationData');
		void loadMinecraftVersions();
		void loadJreComponents();
		void refreshRecommendedRuntime();
	});
</script>

<form onsubmit={nextStep}>
	<Field.Set>
		<Field.Legend>Software Configuration</Field.Legend>
		<Field.Description>Choose server software and Minecraft version.</Field.Description>
		<Field.Group>
			<Field.Field>
				<Field.Label for="software">Server Software</Field.Label>
				<Select.Root type="single" bind:value={() => serverSoftware, setServerSoftware}>
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
					bind:value={() => selectedVersion, setSelectedVersion}
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
					<Checkbox id="terms" bind:checked={() => snapshots, setSnapshots} />
					<Label for="terms">Show snapshots</Label>
				</div>
			</Field.Field>
			<Accordion.Root type="single">
				<Accordion.Item value="item-1">
                    <!-- maybe the WORST POSSIBLE UX EVER -@technodot -->
                    <!-- TODO: too busy to fix rn but i WILL redo ts later -->
					<Accordion.Trigger>Advanced options (Configure Java runtime)</Accordion.Trigger>
					<Accordion.Content>
						<p>
							By default we use the recommended Java runtime for your selected server version. You
							can override it manually if needed.
						</p>
						<div class="flex items-center gap-3 pt-3">
							<Checkbox id="use-recommended-runtime" bind:checked={useRecommendedRuntime} />
							<Label for="use-recommended-runtime">Use recommended Java runtime</Label>
						</div>

						{#if !selectedServerUid}
							<p class="pt-3 text-sm text-muted-foreground">
								Pick server software and version to fetch the recommended runtime.
							</p>
						{:else if isLoadingRecommendedJre}
							<p class="pt-3 text-sm text-muted-foreground">Fetching recommended runtime...</p>
						{:else if recommendedJreError}
							<p class="pt-3 text-sm text-destructive">{recommendedJreError}</p>
						{:else if recommendedRuntimeLabel}
							<p class="pt-3 text-sm text-muted-foreground">
								Recommended runtime: <span class="font-medium text-foreground"
									>{recommendedRuntimeLabel}</span
								>
							</p>
						{:else}
							<p class="pt-3 text-sm text-muted-foreground">
								No recommended runtime is available for the selected server version.
							</p>
						{/if}

						{#if !useRecommendedRuntime}
							<Field.Field class="pt-3">
								<Field.Label for="runtime-type">Java Runtime Type</Field.Label>
								<Select.Root
									type="single"
									bind:value={() => selectedRuntimeType, setRuntimeType}
									disabled={isLoadingJres || runtimeTypeOptions.length === 0}
								>
									<Select.Trigger id="runtime-type">
										{#if isLoadingJres}
											Loading runtime types...
										{:else}
											{runtimeTypeLabel}
										{/if}
									</Select.Trigger>
									<Select.Content
										side="bottom"
										class="max-h-72 [--bits-select-anchor-height:18rem]"
									>
										{#each runtimeTypeOptions as runtimeType (runtimeType.value)}
											<Select.Item value={runtimeType.value} label={runtimeType.label} />
										{/each}
									</Select.Content>
								</Select.Root>
								{#if jresError}
									<p class="text-sm text-destructive">{jresError}</p>
								{:else if !isLoadingJres && runtimeTypeOptions.length === 0}
									<p class="text-sm text-muted-foreground">No Java runtime types are available.</p>
								{/if}
							</Field.Field>

							<Field.Field class="pt-3">
								<Field.Label for="runtime-version">Java Runtime Version</Field.Label>
								<Select.Root
									type="single"
									bind:value={() => selectedRuntimeVersion, setRuntimeVersion}
									disabled={isLoadingJres ||
										runtimeTypeOptions.length === 0 ||
										runtimeVersionsForSelectedType.length === 0}
								>
									<Select.Trigger id="runtime-version">
										{#if isLoadingJres}
											Loading runtime versions...
										{:else}
											{runtimeVersionLabel}
										{/if}
									</Select.Trigger>
									<Select.Content
										side="bottom"
										class="max-h-72 [--bits-select-anchor-height:18rem]"
									>
										{#each runtimeVersionsForSelectedType as runtimeVersion (runtimeVersion.uid)}
											<Select.Item
												value={runtimeVersion.version}
												label={runtimeVersion.display_version}
											/>
										{/each}
									</Select.Content>
								</Select.Root>
								{#if !isLoadingJres && selectedRuntimeType && runtimeVersionsForSelectedType.length === 0}
									<p class="text-sm text-muted-foreground">
										No Java runtime versions are available for the selected runtime type.
									</p>
								{/if}
							</Field.Field>
						{/if}
					</Accordion.Content>
				</Accordion.Item>
			</Accordion.Root>
		</Field.Group>
		<AlertDialog.Root>
			<AlertDialog.Trigger
				type="button"
				class={cn(buttonVariants({ variant: 'default' }), 'mt-6 w-full')}
				disabled={!selectedVersion || isLoadingVersions}
			>
				Next
			</AlertDialog.Trigger>
			<AlertDialog.Content>
				<AlertDialog.Header>
					<AlertDialog.Title>Confirm component installation</AlertDialog.Title>
					<AlertDialog.Description>
						<p>This action will install the selected components:</p>
						<ul class="list-disc pt-2 pl-5">
							<li>
								Server: <span class="font-medium text-foreground"
									>{selectedServerComponent?.display_name ?? 'None'}</span
								>
							</li>
							<li>
								JRE: <span class="font-medium text-foreground">
									{#if effectiveRuntimeUid}
										{jreUidToComponent[effectiveRuntimeUid]?.display_name ?? effectiveRuntimeUid}
									{:else}
										None
									{/if}
								</span>
							</li>
						</ul>
					</AlertDialog.Description>
				</AlertDialog.Header>
				<AlertDialog.Footer>
					<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
					<AlertDialog.Action onclick={submitComponentInstallation}>Continue</AlertDialog.Action>
				</AlertDialog.Footer>
			</AlertDialog.Content>
		</AlertDialog.Root>
	</Field.Set>
</form>
