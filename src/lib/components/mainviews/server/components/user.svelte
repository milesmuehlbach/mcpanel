<script lang="ts">
	import * as Avatar from '$lib/components/ui/avatar/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button, buttonVariants } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { onMount } from 'svelte';
	import { navigate } from 'svelte5-router';

	let { username = 'User', class: className }: { username?: string; class?: string } = $props();
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
		navigate('/login', { replace: true });
	}
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger>
		<Avatar.Root class={className}>
			<Avatar.Fallback>{getInitial(displayName)}</Avatar.Fallback>
		</Avatar.Root>
	</DropdownMenu.Trigger>
	<DropdownMenu.Content>
		<DropdownMenu.Group>
			<DropdownMenu.Label>Hello, {displayName}.</DropdownMenu.Label>
			<DropdownMenu.Separator />
			<Dialog.Root>
				<form action="/api/v1/auth/reset-password">
					<Dialog.Trigger><DropdownMenu.Item>Reset Password</DropdownMenu.Item></Dialog.Trigger>
					<Dialog.Content class="m:max-w-[425px]">
						<Dialog.Header>
							<Dialog.Title>Reset Password</Dialog.Title>
							<Dialog.Description>
								Please enter your current password and a new password.
							</Dialog.Description>
						</Dialog.Header>
						<div class="grid gap-4">
							<div class="grid gap-3">
								<Label for="currentpassword">Current Password</Label>
								<Input id="currentpassword" name="currentpassword" defaultValue="••••••••" />
							</div>
							<div class="grid gap-3">
								<Label for="newpassword">Username</Label>
								<Input id="newpassword" name="newpassword" defaultValue="••••••••" />
							</div>
							<div class="grid gap-3">
								<Label for="pwconfirm">Confirm New Password</Label>
								<Input id="pwconfirm" name="pwconfirm" defaultValue="••••••••" />
							</div>
						</div>
						<Dialog.Footer>
							<Dialog.Close type="button" class={buttonVariants({ variant: 'outline' })}>
								Cancel
							</Dialog.Close>
							<Button type="submit">Reset Password</Button>
						</Dialog.Footer>
					</Dialog.Content>
				</form>
			</Dialog.Root>
			<DropdownMenu.Item onclick={handleLogout}>Logout</DropdownMenu.Item>
		</DropdownMenu.Group>
	</DropdownMenu.Content>
</DropdownMenu.Root>
