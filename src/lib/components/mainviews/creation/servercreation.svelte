<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import * as Field from '$lib/components/ui/field';
	import * as Progress from '$lib/components/ui/progress';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import Step1 from '$lib/components/mainviews/creation/step1.svelte';
	import CheckCircle2Icon from '@lucide/svelte/icons/check-circle-2';
	import CircleIcon from '@lucide/svelte/icons/circle';
	import Loader2Icon from '@lucide/svelte/icons/loader-2';
	import XCircleIcon from '@lucide/svelte/icons/x-circle';
	import { navigate } from 'svelte5-router';
	import { toast } from 'svelte-sonner';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Label } from '$lib/components/ui/label';

	const totalSteps = 3;
	let step = $state(1);
	let isInstalling = $state(false);
	let installError = $state<string | null>(null);
	let stepTwoComplete = $state(false);
	let installationStarted = $state(false);

	let serverName = $state('');
	let isCreatingInstance = $state(false);

	type Hashes = {
		md5: string | null;
		sha1: string | null;
		sha256: string | null;
	};

	type StoredComponent = {
		component_uid: string;
		component_version: string;
		hashes: Hashes;
	};

	type InstallationData = {
		server: StoredComponent;
		runtime: StoredComponent | null;
	};

	type InstallStatus = 'pending' | 'running' | 'succeeded' | 'failed';

	type InstallItem = {
		key: string;
		label: string;
		uid: string;
		hashes: Hashes;
		status: InstallStatus;
		message: string;
		taskId: string | null;
	};

	let installationData = $state<InstallationData | null>(null);
	let installItems = $state<InstallItem[]>([]);

	let eulachecked = $state(false);

	const canConfigureInstance = $derived(stepTwoComplete && !isInstalling);

	const stepTwoProgress = $derived.by(() => {
		if (installItems.length === 0) {
			return 0;
		}

		const completed = installItems.filter((item) => item.status === 'succeeded').length;
		const hasActive = installItems.some((item) => item.status === 'running');
		const inFlight = hasActive ? 0.5 : 0;

		return Math.round(((completed + inFlight) / installItems.length) * 100);
	});

	function getStoredToken(): string | null {
		return sessionStorage.getItem('token');
	}

	function authHeaders(): Record<string, string> {
		const token = getStoredToken();
		if (!token) {
			throw new Error('Missing auth token. Please log in again.');
		}

		return {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		};
	}

	function parseInstallationData(): InstallationData | null {
		const raw = sessionStorage.getItem('installationData');
		if (!raw) {
			return null;
		}

		try {
			const parsed = JSON.parse(raw) as InstallationData;
			if (!parsed?.server?.component_uid) {
				return null;
			}

			return parsed;
		} catch {
			return null;
		}
	}

	function buildInstallItems(data: InstallationData): InstallItem[] {
		const items: InstallItem[] = [
			{
				key: 'server',
				label: 'Minecraft server',
				uid: data.server.component_uid,
				hashes: data.server.hashes,
				status: 'pending',
				message: 'Waiting to start...',
				taskId: null
			}
		];

		if (data.runtime) {
			items.unshift({
				key: 'runtime',
				label: 'Java runtime',
				uid: data.runtime.component_uid,
				hashes: data.runtime.hashes,
				status: 'pending',
				message: 'Waiting to start...',
				taskId: null
			});
		}

		return items;
	}

	function updateInstallItem(key: string, patch: Partial<InstallItem>): void {
		installItems = installItems.map((item) => (item.key === key ? { ...item, ...patch } : item));
	}

	function delay(ms: number): Promise<void> {
		return new Promise((resolve) => window.setTimeout(resolve, ms));
	}

	async function pollTask(taskId: string): Promise<void> {
		for (let attempt = 0; attempt < 600; attempt += 1) {
			const response = await fetch(`/api/v1/tasks/status?task_id=${encodeURIComponent(taskId)}`, {
				headers: authHeaders()
			});

			if (!response.ok) {
				throw new Error('Failed to read install task status.');
			}

			const data = await response.json();
			const task = data?.task;
			const state = task?.state as string | undefined;

			if (state === 'succeeded') {
				return;
			}

			if (state === 'failed') {
				throw new Error(task?.error || 'Component install failed.');
			}

			await delay(1200);
		}

		throw new Error('Component install timed out. Please try again.');
	}

	function buildInstallPayload(uid: string, hashes: Hashes): Record<string, string> {
		const payload: Record<string, string> = { uid };

		if (uid.startsWith('jre:')) {
			if (!hashes.sha256) {
				throw new Error('Missing sha256 for Java runtime install.');
			}
			payload.sha256 = hashes.sha256;
		}

		if (uid.startsWith('server:mojang:')) {
			if (!hashes.sha1) {
				throw new Error('Missing sha1 for Mojang server install.');
			}
			payload.sha1 = hashes.sha1;
		}

		return payload;
	}

	async function installComponent(item: InstallItem): Promise<void> {
		updateInstallItem(item.key, {
			status: 'running',
			message: 'Downloading and installing...',
			taskId: null
		});

		const response = await fetch('/api/v1/components/install', {
			method: 'POST',
			headers: authHeaders(),
			body: JSON.stringify(buildInstallPayload(item.uid, item.hashes))
		});

		if (!response.ok) {
			const data = await response.json().catch(() => null);
			throw new Error(data?.detail || `Failed to queue install for ${item.label}.`);
		}

		const data = await response.json();
		const taskId = data?.task_id as string | undefined;

		if (!taskId) {
			throw new Error(`Install task missing for ${item.label}.`);
		}

		updateInstallItem(item.key, {
			taskId,
			message: 'Installing...'
		});

		await pollTask(taskId);

		updateInstallItem(item.key, {
			status: 'succeeded',
			message: 'Installed'
		});
	}

	async function startInstallation(): Promise<void> {
		if (isInstalling) {
			return;
		}

		const data = parseInstallationData();
		installationData = data;

		if (!data || !data.runtime) {
			stepTwoComplete = false;
			installationStarted = false;
			installItems = [];
			installError =
				'Set a server and Java runtime in Step 1 first, then continue to downloading and installing.';
			return;
		}

		installItems = buildInstallItems(data);
		installError = null;
		stepTwoComplete = false;
		installationStarted = true;
		isInstalling = true;

		try {
			for (const item of installItems) {
				await installComponent(item);
			}

			stepTwoComplete = true;
		} catch (error) {
			const message = error instanceof Error ? error.message : 'Installation failed. Please retry.';
			installError = message;

			const failed = installItems.find((item) => item.status === 'running')?.key;
			if (failed) {
				updateInstallItem(failed, {
					status: 'failed',
					message: message
				});
			}

			toast.error(message);
		} finally {
			isInstalling = false;
		}
	}

	function goToServers(): void {
		navigate('/servers');
	}

	function goToServerDashboard(serverUuid: string): void {
		navigate(`/servers/${serverUuid}/dashboard`);
	}

	async function createInstance(): Promise<void> {
		if (
			!installationData ||
			!installationData.runtime ||
			!canConfigureInstance ||
			isCreatingInstance
		) {
			return;
		}

		const trimmedName = serverName.trim();
		if (!trimmedName) {
			toast.error('Please enter a server name.');
			return;
		}

		isCreatingInstance = true;

		try {
			const response = await fetch('/api/v1/instances/create', {
				method: 'POST',
				headers: authHeaders(),
				body: JSON.stringify({
					server_uid: installationData.server.component_uid,
					java_uid: installationData.runtime.component_uid,
					name: trimmedName
				})
			});

			if (!response.ok) {
				const data = await response.json().catch(() => null);
				throw new Error(data?.detail || 'Failed to create instance.');
			}

			const data = await response.json();
			const createdInstanceUuid = data?.uuid ?? null;
			sessionStorage.removeItem('installationData');
			toast.success('Instance created successfully.');

			if (typeof createdInstanceUuid === 'string' && createdInstanceUuid.trim()) {
				goToServerDashboard(createdInstanceUuid);
			} else {
				goToServers();
			}
		} catch (error) {
			const message = error instanceof Error ? error.message : 'Failed to create instance.';
			toast.error(message);
		} finally {
			isCreatingInstance = false;
		}
	}

	function goToStep(nextStep: number) {
		const clampedStep = Math.min(totalSteps, Math.max(1, nextStep));

		if (clampedStep === 3 && !canConfigureInstance) {
			return;
		}

		step = clampedStep;

		if (step === 2 && !installationStarted) {
			void startInstallation();
		}
	}

	function incrementStep() {
		goToStep(step + 1);
	}

	function retryInstallation(): void {
		installationStarted = false;
		void startInstallation();
	}
</script>

<div class="flex min-h-screen w-full items-center justify-center bg-background p-4 sm:p-8">
	<Card.Root class="w-full max-w-2xl">
		<Card.Content class="min-h-56">
			{#if step === 1}
				<Step1 {incrementStep} />
			{:else if step === 2}
				<div class="space-y-5">
					<div class="space-y-2">
						<Field.Legend>Component Download</Field.Legend>
						<Field.Description>Your components are downloading. Please wait.</Field.Description>
					</div>

					<Progress.Root value={stepTwoProgress} class="h-2" />

					<div class="space-y-3">
						{#if installItems.length === 0 && !installError}
							<div class="rounded-md border p-3 text-sm text-muted-foreground">
								Preparing install list...
							</div>
						{/if}

						{#each installItems as item (item.key)}
							<div class="flex items-start gap-3 rounded-md border p-3">
								{#if item.status === 'succeeded'}
									<CheckCircle2Icon class="mt-0.5 size-4 text-green-500" />
								{:else if item.status === 'failed'}
									<XCircleIcon class="mt-0.5 size-4 text-destructive" />
								{:else if item.status === 'running'}
									<Loader2Icon class="mt-0.5 size-4 animate-spin text-primary" />
								{:else}
									<CircleIcon class="mt-0.5 size-4 animate-spin text-muted-foreground" />
								{/if}
								<div class="min-w-0 flex-1">
									<p class="font-medium">{item.label}</p>
									<p class="truncate text-sm text-muted-foreground">{item.uid}</p>
									<p class="text-sm text-muted-foreground">{item.message}</p>
								</div>
							</div>
						{/each}
					</div>

					{#if installError}
						<div
							class="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
						>
							{installError}
						</div>
					{/if}

					<div class="flex flex-wrap gap-2">
						{#if stepTwoComplete}
							<Button type="button" onclick={() => goToStep(3)}>Next</Button>
						{:else}
							<Button
								type="button"
								variant="outline"
								onclick={retryInstallation}
								disabled={isInstalling}
								>{isInstalling ? 'Installing...' : 'Retry installation'}</Button
							>
						{/if}
					</div>
				</div>
			{:else}
				<div class="space-y-5">
					<Field.Set>
						<Field.Legend>Configure Instance</Field.Legend>
						<Field.Description>Please enter server name.</Field.Description>
						<Field.Field>
							<Field.Label for="server-name">Server Name</Field.Label>
							<Input id="server-name" bind:value={serverName} placeholder="My Server" />
						</Field.Field>
					</Field.Set>
					<div class="flex items-start gap-3">
						<Checkbox id="terms-2" bind:checked={eulachecked} />
						<div class="grid gap-2">
							<Label for="terms-2">Agree to Minecraft EULA</Label>
							<p class="text-sm text-muted-foreground">
								By clicking this checkbox, you agree to the terms and conditions as outlined in the <a
									target="_blank"
									href="https://www.minecraft.net/en-us/eula"
									class="text-gray-50 underline">Minecraft EULA</a
								>
							</p>
						</div>
					</div>
					<div class="flex flex-wrap gap-2 pt-2">
						<Button
							type="button"
							class="w-full"
							onclick={createInstance}
							disabled={isCreatingInstance || !serverName.trim() || !eulachecked}
						>
							{#if isCreatingInstance}
								<Loader2Icon class="mr-2 size-4 animate-spin" />
								Creating instance...
							{:else}
								Create Server
							{/if}
						</Button>
					</div>
				</div>
			{/if}
		</Card.Content>
	</Card.Root>
</div>
