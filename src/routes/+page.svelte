<script lang="ts">
	import ServerView from '$lib/components/mainviews/server/serverview.svelte';
	import LoginView from '$lib/components/mainviews/login.svelte';
	import OnboardingView from '$lib/components/mainviews/onboard.svelte';
	import ServerCreationView from '$lib/components/mainviews/creation/servercreation.svelte';
	import { Route, Router, listen, navigate } from 'svelte5-router';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	const PUBLIC_PATHS = new Set(['/login', '/onboarding']);
	const PRIVATE_PATHS = new Set(['/servers', '/servers/new']);

	let initialized = $state(false);
	let currentPath = $state('/');

	let isDirty = $derived(currentPath === '/servers/new');

	function normalizePath(pathname: string): string {
		if (pathname.length > 1 && pathname.endsWith('/')) {
			return pathname.slice(0, -1);
		}

		return pathname || '/';
	}

	function go(to: string, replace = true): void {
		const target = normalizePath(to);
		currentPath = target;
		navigate(target, { replace });
	}

	function newServer(): void {
		go('/servers/new', false);
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
		currentPath = normalizePath(window.location.pathname);
		const unlisten = listen(({ location }) => {
			currentPath = normalizePath(location.pathname);
		});

		void (async () => {
			const allowed = await isOnboardingAllowed();
			if (allowed) {
				go('/onboarding');
				initialized = true;
				return;
			}

			const hadToken = !!getStoredToken();
			const expired = await isTokenExpired();
			if (!expired) {
				if (PRIVATE_PATHS.has(currentPath)) {
					initialized = true;
					return;
				}

				go('/servers');
			} else {
				if (hadToken) {
					toast.error('Session Expired. Please log in again.');
				}
				clearStoredToken();
				go('/login');
			}
			initialized = true;
		})();

		return () => {
			unlisten();
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
{:else}
	<Router>
		<Route path="/servers/new">
			<ServerCreationView />
		</Route>
		<Route path="/servers">
			<ServerView {newServer} />
		</Route>
		<Route path="/login">
			<div class="flex h-screen w-full items-center justify-center px-4">
				<LoginView
					onSuccess={() => {
						go('/servers', false);
						toast.success('Login Successful!');
					}}
				/>
			</div>
		</Route>
		<Route path="/onboarding">
			<div class="flex h-screen w-full items-center justify-center px-4">
				<OnboardingView
					onSuccess={() => {
						go('/login');
						toast.success('Registration Successful!');
					}}
				/>
			</div>
		</Route>
		<Route>
			<div class="flex h-screen w-full items-center justify-center px-4">
				{#if PUBLIC_PATHS.has(currentPath)}
					<LoginView
						onSuccess={() => {
							go('/servers', false);
							toast.success('Login Successful!');
						}}
					/>
				{:else}
					<div class="text-sm text-muted-foreground">Unknown route. Redirecting...</div>
				{/if}
			</div>
		</Route>
	</Router>
{/if}
