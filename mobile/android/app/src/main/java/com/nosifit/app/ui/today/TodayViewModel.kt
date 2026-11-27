package com.nosifit.app.ui.today

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.nosifit.app.data.DashboardRepository
import com.nosifit.app.data.DashboardToday
import com.nosifit.app.ui.messageFor
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class TodayUiState(
    val today: DashboardToday? = null,
    val loading: Boolean = false,
    val error: Int? = null,
)

class TodayViewModel(private val dashboard: DashboardRepository) : ViewModel() {
    private val _state = MutableStateFlow(TodayUiState())
    val state: StateFlow<TodayUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        if (_state.value.loading) return
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            _state.value = try {
                TodayUiState(today = dashboard.today())
            } catch (e: Exception) {
                _state.value.copy(loading = false, error = messageFor(e))
            }
        }
    }
}
