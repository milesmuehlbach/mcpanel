<script lang="ts">
	import ServerView from '$lib/components/mainviews/server/serverview.svelte';
	import LoginView from '$lib/components/mainviews/login.svelte';
	import OnboardingView from '$lib/components/mainviews/onboard.svelte';
	import ServerCreationView from '$lib/components/mainviews/creation/servercreation.svelte';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	type View = 'server' | 'login' | 'servercreation' | 'onboarding';

	const VALID_VIEWS: View[] = ['server', 'login', 'servercreation', 'onboarding'];

	let initialized = $state(false);
	let view = $state<View>('login');

	let isDirty = $derived(view === 'servercreation');

	function getViewFromUrl(): View {
		const url = new URL(window.location.href);
		const urlView = url.searchParams.get('view');

		if (urlView && VALID_VIEWS.includes(urlView as View)) {
			return urlView as View;
		}

		return 'login';
	}

	function setView(newView: View, replaceState = true) {
		view = newView;
		const url = new URL(window.location.href);
		url.searchParams.set('view', newView);

		const target = `${url.pathname}${url.search}${url.hash}`;
		if (replaceState) {
			window.history.replaceState(window.history.state, '', target);
			return;
		}

		window.history.pushState(window.history.state, '', target);
	}

	function newServer() {
		setView('servercreation');
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
		view = getViewFromUrl();

		const onPopState = () => {
			view = getViewFromUrl();
		};

		window.addEventListener('popstate', onPopState);

		void (async () => {
			const allowed = await isOnboardingAllowed();
			if (allowed) {
				setView('onboarding');
				initialized = true;
				return;
			}

			const hadToken = !!getStoredToken();
			const expired = await isTokenExpired();
			if (!expired) {
				setView('server');
			} else {
				if (hadToken) {
					toast.error('Session Expired. Please log in again.');
				}
				clearStoredToken();
				setView('login');
			}
			initialized = true;
		})();

		return () => {
			window.removeEventListener('popstate', onPopState);
		};
	});
</script>

<svelte:window
	onbeforeunload={(e) => {
		if (isDirty) {
			e.preventDefault();
		}
	}}
/>

{#if !initialized}
	<div class="flex h-screen w-full items-center justify-center px-4"></div>
{:else if view === 'server'}
	<ServerView {newServer} />
{:else if view === 'login'}
	<div class="flex h-screen w-full items-center justify-center px-4">
		<LoginView
			onSuccess={() => {
				setView('server', false);
				toast.success('Login Successful!');
			}}
		/>
	</div>
{:else if view === 'servercreation'}
	<ServerCreationView />
{:else if view === 'onboarding'}
	<div class="flex h-screen w-full items-center justify-center px-4">
		<OnboardingView
			onSuccess={() => {
				setView('login');
				toast.success('Registration Successful!');
			}}
		/>
	</div>
{/if}
