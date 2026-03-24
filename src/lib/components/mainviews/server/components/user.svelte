<script lang="ts">
	import * as Avatar from '$lib/components/ui/avatar/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { onMount } from 'svelte';

	let { username = 'User' }: { username?: string } = $props();
	let displayName = $state('User');

	function getInitial(name: string): string {
		const trimmed = name.trim();
		if (!trimmed) {
			return 'U';
		}

		return trimmed.slice(0, 1).toUpperCase();
	}

	onMount(() => {
		displayName = username?.trim() ? username : 'User';

		void (async () => {
			const token = sessionStorage.getItem('token');
			if (!token) {
				return;
			}

			try {
				const response = await fetch('/api/v1/auth/me', {
					headers: {
						Authorization: `Bearer ${token}`
					}
				});

				if (!response.ok) {
					return;
				}

				const data = (await response.json()) as { user?: { username?: unknown } };
				if (typeof data.user?.username === 'string' && data.user.username.trim()) {
					displayName = data.user.username;
				}
			} catch (error) {
				console.error('Failed to load user profile:', error);
			}
		})();
	});

	async function handleLogout() {
		sessionStorage.removeItem('token');
		window.location.reload();
	}
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger>
		<Avatar.Root>
			<Avatar.Fallback>{getInitial(displayName)}</Avatar.Fallback>
		</Avatar.Root>
	</DropdownMenu.Trigger>
	<DropdownMenu.Content>
		<DropdownMenu.Group>
			<DropdownMenu.Label>Hello, {displayName}.</DropdownMenu.Label>
			<DropdownMenu.Separator />
			<DropdownMenu.Item>Reset Password</DropdownMenu.Item>
			<DropdownMenu.Item onclick={handleLogout}>Logout</DropdownMenu.Item>
		</DropdownMenu.Group>
	</DropdownMenu.Content>
</DropdownMenu.Root>
