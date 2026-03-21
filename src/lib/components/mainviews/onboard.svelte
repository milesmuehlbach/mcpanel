<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import {
		FieldGroup,
		Field,
		FieldLabel,
		FieldDescription,
		FieldError
	} from '$lib/components/ui/field/index.js';

	let { onSuccess = () => {} }: { onSuccess?: () => void } = $props();

	let username = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let errordis = $state('');
	const usernameRegex = /^[A-Za-z0-9_-]+$/;
	let isUsernameValid = $derived(username === '' || usernameRegex.test(username));
	let passwordsMatch = $derived(password === confirmPassword);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();

		if (!usernameRegex.test(username)) {
			console.error('Invalid username');
			return;
		}
		if (!passwordsMatch) {
			console.error('Passwords do not match');
			return;
		}

		try {
			const response = await fetch('/api/v1/auth/onboarding', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ username, password })
			});

			if (response.ok) {
				const data = await response.json();
				console.log('Register successful:', data);
				errordis = 'Register Successful : ' + data.message;
				onSuccess();
			} else {
				const error = await response.json();
				console.error('Register failed:', error);
				errordis = 'Register failed: ' + error.message;
			}
		} catch (err) {
			console.error('An error occurred during login: ', err);
		}
	}
</script>

<Card.Root class="mx-auto w-full max-w-sm">
	<Card.Header>
		<Card.Title class="text-2xl">MCPanel Admin Setup</Card.Title>
	</Card.Header>
	<Card.Content>
		<form onsubmit={handleSubmit}>
			<FieldGroup>
				<Field>
					<FieldLabel for="username">Username</FieldLabel>
					<Input
						id="username"
						name="username"
						type="text"
						placeholder="Username"
						required
						bind:value={username}
						pattern="[-A-Za-z0-9_]+"
					/>
					{#if !isUsernameValid}
						<FieldDescription class="text-destructive">
							Username must only contain a-z, A-Z, 0-9, _ and -
						</FieldDescription>
					{/if}
				</Field>
				<Field>
					<div class="flex items-center">
						<FieldLabel for="password">Password</FieldLabel>
					</div>
					<Input
						id="password"
						name="password"
						type="password"
						required
						placeholder="Password"
						bind:value={password}
					/>
				</Field>
				<Field>
					<div class="flex items-center">
						<FieldLabel for="confirm-password">Confirm Password</FieldLabel>
					</div>
					<Input
						id="confirm-password"
						name="confirmPassword"
						type="password"
						required
						placeholder="Confirm Password"
						bind:value={confirmPassword}
					/>
					{#if !passwordsMatch && confirmPassword !== ''}
						<FieldDescription class="text-destructive">Passwords do not match</FieldDescription>
					{/if}
				</Field>
				<Field>
					<Button
						type="submit"
						class="w-full"
						disabled={!isUsernameValid ||
							username === '' ||
							password === '' ||
							!passwordsMatch ||
							confirmPassword === ''}
					>
						Register Admin User
					</Button>
				</Field>
				<FieldError>{errordis}</FieldError>
			</FieldGroup>
		</form>
	</Card.Content>
</Card.Root>
