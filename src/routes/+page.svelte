<script lang="ts">
	import ServerView from '$lib/components/mainviews/server/serverview.svelte';
	import LoginView from '$lib/components/mainviews/login.svelte';
	import OnboardingView from '$lib/components/mainviews/onboard.svelte';
	import { onMount } from 'svelte';

	type View = 'server' | 'login' | 'servercreation' | 'onboarding';

	let view = $state<View>('login');

	async function isOnboardingAllowed(): Promise<boolean> {
		try {
			const response = await fetch('/api/v1/auth/onboarding');

			if (!response.ok) {
				return false;
			}

			const data = await response.json();
			return data.status;
		} catch (error) {
			console.error('Error checking onboarding status:', error);
			return false;
		}
	}

	onMount(() => {
		void (async () => {
			const allowed = await isOnboardingAllowed();
			view = allowed ? 'onboarding' : 'login';
		})();
	});
</script>

{#if view === 'server'}
	<ServerView />
{:else if view === 'login'}
	<div class="flex h-screen w-full items-center justify-center px-4">
		<LoginView
			onSuccess={() => {
				view = 'server';
			}}
		/>
	</div>
{:else if view === 'servercreation'}
	<h1>Server Creation Placeholder</h1>
{:else if view === 'onboarding'}
	<div class="flex h-screen w-full items-center justify-center px-4">
		<OnboardingView
			onSuccess={() => {
				view = 'login';
			}}
		/>
	</div>
{/if}
