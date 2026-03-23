<script lang="ts">
	import ServerView from '$lib/components/mainviews/server/serverview.svelte';
	import LoginView from '$lib/components/mainviews/login.svelte';
	import OnboardingView from '$lib/components/mainviews/onboard.svelte';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	type View = 'server' | 'login' | 'servercreation' | 'onboarding';

	let view = $state<View>('login');

	let isDirty = $derived(view === 'servercreation');

	function newServer() {
		view = 'servercreation';
		return;
	}

	function getStoredToken(): string | null {
		return sessionStorage.getItem('token');
	}

	function clearStoredToken(): void {
		sessionStorage.removeItem('token');
	}

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

	async function isTokenExpired(): Promise<boolean> {
		const token = getStoredToken();

		if (!token) {
			return true;
		}

		try {
			const response = await fetch('/api/v1/auth/me', {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				return true;
			}
			const data = await response.json();
			return !data.status;
		} catch (error) {
			console.error('Error validating token:', error);
			return true;
		}
	}

	onMount(() => {
		void (async () => {
			const allowed = await isOnboardingAllowed();
			view = allowed ? 'onboarding' : 'login';

			if (allowed) {
				return;
			}

			const hadToken = !!getStoredToken();
			const expired = await isTokenExpired();
			if (!expired) {
				view = 'server';
			} else {
				if (hadToken) {
					toast.error('Session Expired. Please log in again.');
				}
				clearStoredToken();
				view = 'login';
			}
		})();
	});
</script>

<svelte:window
	onbeforeunload={(e) => {
		if (isDirty) {
			e.preventDefault();
		}
	}}
/>

{#if view === 'server'}
	<ServerView {newServer} />
{:else if view === 'login'}
	<div class="flex h-screen w-full items-center justify-center px-4">
		<LoginView
			onSuccess={() => {
				view = 'server';
				toast.success('Login Successful!');
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
				toast.success('Registration Successful!');
			}}
		/>
	</div>
{/if}
